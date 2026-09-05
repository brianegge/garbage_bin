import contextlib
import json
import logging
import os
import shutil
import time
from datetime import date, datetime
from io import BytesIO

import requests
import torch
from PIL import Image
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

LOCAL_FALLBACK = "/data/local"

# Confidence floor for reporting a detection.
DETECTION_THRESHOLD = 0.4
# A person who is only partly visible still occludes whatever is behind them,
# so report them well below the threshold used to decide whether a vehicle is
# present.
PERSON_THRESHOLD = 0.25

# Module-level session for connection reuse
_session = None


def get_session():
    """Get or create a reusable HTTP session."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def sanitize(j: dict[str, any]) -> dict[str, any]:
    o = {}
    for k, v in j.items():
        o[k.replace(" ", "_")] = v
    return o


def save(path, image, predictions):
    """Save image and predictions to disk.

    Returns:
        True if saved to the NFS path, False if fell back to local storage.
    """
    good_predictions = dict(filter(lambda elem: elem[1] > 0.8, predictions.items()))
    detected_objects = list(good_predictions.keys())
    detected_objects = list(filter(lambda x: x != "something", detected_objects))
    datedir = date.today().strftime("%Y%m%d")
    pathname = os.path.join(path, datedir)
    nfs_ok = True
    try:
        os.makedirs(pathname, exist_ok=True)
        # Test that the path is actually writable (catches stale NFS)
        testfile = os.path.join(pathname, ".write_test")
        open(testfile, "w").close()
        os.remove(testfile)
    except OSError as e:
        logging.warning(
            "NFS path unavailable (%s), falling back to %s", e, LOCAL_FALLBACK
        )
        pathname = os.path.join(LOCAL_FALLBACK, datedir)
        try:
            os.makedirs(pathname, exist_ok=True)
        except OSError as e2:
            logging.error("Local fallback also unavailable: %s", e2)
            return False
        nfs_ok = False
    basename = os.path.join(
        pathname,
        datetime.now().strftime("%H%M%S")
        + "-"
        + "garage_check"
        + "-"
        + "_".join(detected_objects).lower(),
    )
    logging.info("Saving %s", basename)
    try:
        image.save(basename + ".jpg")
        with open(basename + ".txt", "w") as file:
            file.write(json.dumps(predictions))
    except OSError as e:
        logging.error("Failed to save detection output to %s: %s", basename, e)
        return False
    return nfs_ok


def sync_local_to_remote(remote_path):
    """Move files from local fallback to the remote NFS path when it's available.

    Returns:
        True if the remote path is writable, False otherwise.
    """
    if not os.path.exists(LOCAL_FALLBACK):
        return True
    dirs = os.listdir(LOCAL_FALLBACK)
    if not dirs:
        return True
    # Check if remote path is writable
    try:
        os.makedirs(remote_path, exist_ok=True)
        testfile = os.path.join(remote_path, ".write_test")
        open(testfile, "w").close()
        os.remove(testfile)
    except OSError:
        return False
    for datedir in dirs:
        src_dir = os.path.join(LOCAL_FALLBACK, datedir)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(remote_path, datedir)
        os.makedirs(dst_dir, exist_ok=True)
        for filename in os.listdir(src_dir):
            src = os.path.join(src_dir, filename)
            dst = os.path.join(dst_dir, filename)
            if os.path.exists(dst):
                base, ext = os.path.splitext(dst)
                index = 1
                while os.path.exists(dst):
                    dst = f"{base}_{index}{ext}"
                    index += 1
            try:
                shutil.move(src, dst)
                logging.info("Synced %s -> %s", src, dst)
            except OSError as e:
                logging.warning("Failed to sync %s: %s", src, e)
                return False
        with contextlib.suppress(OSError):
            os.rmdir(src_dir)
    return True


# How long to stop trying a failed primary source before probing it again.
# Without this the primary's full timeout is paid on every cycle while it is
# down, which stretches a 5s cycle past 15s and starves the detector.
PRIMARY_COOLDOWN_SECONDS = 300.0
_primary_down_until = 0.0


def reset_primary_cooldown():
    """Test hook: forget any recorded primary failure."""
    global _primary_down_until
    _primary_down_until = 0.0


def _fetch(session, url, timeout, resize):
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    if resize:
        width, height = (int(d) for d in resize.lower().split("x"))
        if img.size != (width, height):
            img = img.resize((width, height))
    return img


def _auth_for(camera, scheme):
    if scheme == "none":
        return None
    if scheme == "basic":
        return HTTPBasicAuth(camera["user"], camera["password"])
    # curl -v --digest --user "admin:***" "http://garage-cam.home/cgi-bin/snapshot.cgi"
    return HTTPDigestAuth(camera["user"], camera["password"])


def get_image(camera, timeout=15):
    """Fetch a frame from the configured snapshot source, falling back.

    With a `url` key, fetches that URL first — e.g. Blue Iris's
    /image/{shortname} endpoint, which serves its latest decoded frame in
    ~80ms. If that fails and a `host` is configured, falls back automatically
    to the camera's own Dahua snapshot endpoint rather than giving up: an NVR
    is a convenience, not a dependency, and the camera is the source of truth.

    Blue Iris being powered down on 2026-09-05 left this detector blind for
    18h while `host` sat in the config unused, so the fallback is no longer
    something you enable by editing a file.

    The failed primary is skipped for PRIMARY_COOLDOWN_SECONDS before being
    retried, so a long outage costs one timeout every five minutes instead of
    one per cycle.

    `auth` selects the scheme for the primary: digest (default, Dahua), basic,
    or none (Blue Iris with anonymous LAN access). The direct fallback always
    uses digest, since that is what the cameras speak.

    `resize` (e.g. 2592x1944) restores the native camera geometry: Blue Iris
    serves this camera stretched to 3464x1944 and the model was trained on 4:3
    frames. It is a no-op on the direct path, which is already native.
    """
    global _primary_down_until
    session = get_session()
    resize = camera.get("resize")
    primary = camera.get("url")
    direct = f"http://{camera['host']}/cgi-bin/snapshot.cgi" if camera.get("host") else None

    if primary and direct and time.monotonic() < _primary_down_until:
        primary = None  # still cooling down; go straight to the camera

    if primary:
        session.auth = _auth_for(camera, camera.get("auth", "digest"))
        try:
            img = _fetch(session, primary, timeout, resize)
            _primary_down_until = 0.0
            return img
        except Exception as e:
            if not direct:
                raise
            _primary_down_until = time.monotonic() + PRIMARY_COOLDOWN_SECONDS
            logging.warning(
                "Snapshot source %s failed (%s) — falling back to the camera "
                "directly for %ds",
                primary,
                e,
                int(PRIMARY_COOLDOWN_SECONDS),
            )

    if not direct:
        raise RuntimeError("camera has neither a url nor a host configured")
    session.auth = _auth_for(camera, "digest")
    return _fetch(session, direct, timeout, resize)


def detectframe(model, img):
    if img.mode != "RGB":
        img = img.convert("RGB")
    with torch.no_grad():
        results = model(img)
    boxes = results[0].boxes
    maxes = {}
    something = -1.0
    for box in boxes:
        conf = box.conf.item()
        cls = model.names.get(box.cls.item())
        if cls not in maxes:
            maxes[cls] = conf
        maxes[cls] = max(conf, maxes[cls])
        if cls != "honda civic":
            something = max(something, conf)
    o = dict(filter(lambda item: item[1] > DETECTION_THRESHOLD, maxes.items()))
    if "person" in maxes and maxes["person"] > PERSON_THRESHOLD:
        o["person"] = maxes["person"]
    o["something"] = something
    o = sanitize(o)
    # Explicitly free YOLO results and their tensors
    del boxes, results
    return o, img
