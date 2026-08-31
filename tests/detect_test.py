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


class _Scalar:
    """Stands in for a torch scalar tensor."""

    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class _Box:
    def __init__(self, conf, cls_id):
        self.conf = _Scalar(conf)
        self.cls = _Scalar(cls_id)


class _Results:
    def __init__(self, boxes):
        self.boxes = boxes


class _StubModel:
    """Stands in for YOLO so detections can be set to exact confidences."""

    def __init__(self, names, boxes):
        self.names = names
        self._boxes = boxes

    def __call__(self, img):
        return [_Results(self._boxes)]


def test_detectframe_reports_faint_person():
    model = _StubModel(
        {0.0: "person", 1.0: "honda civic"},
        [_Box(0.3, 0.0), _Box(0.3, 1.0)],
    )
    o, _ = detectframe(model, Image.new("RGB", (32, 32)))
    # Below the 0.4 detection floor, but reported so the caller can hold state.
    assert o["person"] == 0.3
    # A vehicle at the same confidence stays filtered out.
    assert "honda_civic" not in o


def test_detectframe_drops_very_faint_person():
    model = _StubModel({0.0: "person"}, [_Box(0.1, 0.0)])
    o, _ = detectframe(model, Image.new("RGB", (32, 32)))
    assert "person" not in o
