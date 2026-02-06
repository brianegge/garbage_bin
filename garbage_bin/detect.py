import contextlib
import json
import logging
import os
import shutil
from datetime import date, datetime
from io import BytesIO

import requests
from PIL import Image
from requests.auth import HTTPDigestAuth

LOCAL_FALLBACK = "/data/local"

# from flask import g


def sanitize(j: dict[str, any]) -> dict[str, any]:
    o = {}
    for k, v in j.items():
        o[k.replace(" ", "_")] = v
    return o


def save(path, image, predictions):
    good_predictions = dict(filter(lambda elem: elem[1] > 0.8, predictions.items()))
    detected_objects = list(good_predictions.keys())
    detected_objects = list(filter(lambda x: x != "something", detected_objects))
    datedir = date.today().strftime("%Y%m%d")
    pathname = os.path.join(path, datedir)
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
        os.makedirs(pathname, exist_ok=True)
    basename = os.path.join(
        pathname,
        datetime.now().strftime("%H%M%S")
        + "-"
        + "garage_check"
        + "-"
        + "_".join(detected_objects).lower(),
    )
    logging.info("Saving %s", basename)
    # pimg = Image.fromarray(image)
    image.save(basename + ".jpg")
    with open(basename + ".txt", "w") as file:
        file.write(json.dumps(predictions))


def sync_local_to_remote(remote_path):
    """Move files from local fallback to the remote NFS path when it's available."""
    if not os.path.exists(LOCAL_FALLBACK):
        return
    dirs = os.listdir(LOCAL_FALLBACK)
    if not dirs:
        return
    # Check if remote path is writable
    try:
        os.makedirs(remote_path, exist_ok=True)
        testfile = os.path.join(remote_path, ".write_test")
        open(testfile, "w").close()
        os.remove(testfile)
    except OSError:
        return
    for datedir in dirs:
        src_dir = os.path.join(LOCAL_FALLBACK, datedir)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(remote_path, datedir)
        os.makedirs(dst_dir, exist_ok=True)
        for filename in os.listdir(src_dir):
            src = os.path.join(src_dir, filename)
            dst = os.path.join(dst_dir, filename)
            try:
                shutil.move(src, dst)
                logging.info("Synced %s -> %s", src, dst)
            except OSError as e:
                logging.warning("Failed to sync %s: %s", src, e)
                return
        with contextlib.suppress(OSError):
            os.rmdir(src_dir)


def get_image(camera, timeout=60):
    session = requests.Session()
    session.auth = HTTPDigestAuth(camera["user"], camera["password"])
    # curl -v --digest --user "admin:Password1"  "http://garage-cam.home/cgi-bin/snapshot.cgi" -o capture/garage.jpg
    url = f"http://{camera['host']}/cgi-bin/snapshot.cgi"
    response = session.get(url, timeout=timeout)
    img = Image.open(BytesIO(response.content))
    # img = cv2.imdecode(numpy.fromstring(request, numpy.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        return ["Error reading image"]
    return img


def detectframe(model, img):
    # read image file string data
    # url = "http://garage:8085/?action=snapshot"
    # img = imageio.imread(url)
    if img.mode != "RGB":
        img = img.convert("RGB")
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
    o = dict(filter(lambda item: item[1] > 0.4, maxes.items()))
    o["something"] = something
    o = sanitize(o)
    return o, img
