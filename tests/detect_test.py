import os

from PIL import Image
from ultralytics import YOLO

from garbage_bin.detect import detectframe, sanitize


def test_sanitize():
    assert sanitize({"honda crv": 0.9}) == {"honda_crv": 0.9}


def test_detectframe():
    # Get the directory of the current module
    module_dir = os.path.dirname(__file__)

    # Construct the full path to the file
    file_path = os.path.join(module_dir, "garage-cat.jpg")
    img = Image.open(file_path)

    model = YOLO("best.pt")  # pretrained YOLOv8n model
    o, img = detectframe(model, img)
    assert o["garbage_bin"] > 0.9
    assert o["honda_civic"] > 0.9
    assert o["honda_crv"] > 0.9
    assert o["something"] > 0.9
    assert o["tool_bucket"] > 0.9
