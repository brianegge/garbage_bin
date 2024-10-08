import json
import logging
import os
from datetime import date, datetime
from io import BytesIO
from typing import Dict

import requests
from PIL import Image
from requests.auth import HTTPDigestAuth

# from flask import g


def sanitize(j: Dict[str, any]) -> Dict[str, any]:
    o = {}
    for k, v in j.items():
        o[k.replace(" ", "_")] = v
    return o


def save(path, image, predictions):
    good_predictions = dict(filter(lambda elem: elem[1] > 0.8, predictions.items()))
    detected_objects = list(good_predictions.keys())
    detected_objects = list(filter(lambda x: x != "something", detected_objects))
    pathname = os.path.join(path, date.today().strftime("%Y%m%d"))
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


def get_image(camera):
    session = requests.Session()
    session.auth = HTTPDigestAuth(camera["user"], camera["password"])
    # curl -v --digest --user "admin:Password1"  "http://garage-cam.home/cgi-bin/snapshot.cgi" -o capture/garage.jpg
    url = f"http://{camera['host']}/cgi-bin/snapshot.cgi"
    response = session.get(url)
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
        if conf > maxes[cls]:
            maxes[cls] = conf
        if cls != "honda civic":
            something = max(something, conf)
    o = dict(filter(lambda item: item[1] > 0.4, maxes.items()))
    o["something"] = something
    o = sanitize(o)
    return o, img
