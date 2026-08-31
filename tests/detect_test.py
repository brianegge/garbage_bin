import io
import os

from PIL import Image
from ultralytics import YOLO

from garbage_bin.detect import detectframe, get_image, sanitize


def _jpeg_bytes(size=(64, 48)):
    buf = io.BytesIO()
    Image.new("RGB", size, "gray").save(buf, format="JPEG")
    return buf.getvalue()


def _mock_session(mocker, content, status=200):
    session = mocker.Mock()
    response = mocker.Mock()
    response.content = content
    response.status_code = status
    if status >= 400:
        import requests

        response.raise_for_status.side_effect = requests.HTTPError(f"{status}")
    else:
        response.raise_for_status.return_value = None
    session.get.return_value = response
    mocker.patch("garbage_bin.detect.get_session", return_value=session)
    return session


def test_get_image_url_overrides_host(mocker):
    session = _mock_session(mocker, _jpeg_bytes())
    img = get_image({"url": "http://blueiris:81/image/Garage", "auth": "none"})
    session.get.assert_called_once_with("http://blueiris:81/image/Garage", timeout=15)
    assert session.auth is None
    assert img.size == (64, 48)


def test_get_image_defaults_to_dahua_snapshot_with_digest(mocker):
    session = _mock_session(mocker, _jpeg_bytes())
    get_image({"host": "garage-cam.home", "user": "admin", "password": "x"})
    session.get.assert_called_once_with(
        "http://garage-cam.home/cgi-bin/snapshot.cgi", timeout=15
    )
    assert session.auth is not None


def test_get_image_basic_auth(mocker):
    from requests.auth import HTTPBasicAuth

    session = _mock_session(mocker, _jpeg_bytes())
    get_image(
        {
            "url": "http://blueiris:81/image/Garage",
            "auth": "basic",
            "user": "u",
            "password": "p",
        }
    )
    assert isinstance(session.auth, HTTPBasicAuth)


def test_get_image_resizes_stretched_frame(mocker):
    """Blue Iris serves 16:9-stretched frames; restore the native geometry."""
    _mock_session(mocker, _jpeg_bytes(size=(346, 194)))
    img = get_image(
        {"url": "http://blueiris:81/image/Garage", "auth": "none", "resize": "259x194"}
    )
    assert img.size == (259, 194)


def test_get_image_skips_resize_when_already_native(mocker):
    _mock_session(mocker, _jpeg_bytes(size=(64, 48)))
    img = get_image({"url": "http://x/image/Garage", "auth": "none", "resize": "64x48"})
    assert img.size == (64, 48)


def test_get_image_raises_on_http_error(mocker):
    """An auth failure or BI error surfaces as a camera error, not a decode error."""
    import pytest
    import requests

    _mock_session(mocker, b"Unauthorized", status=401)
    with pytest.raises(requests.HTTPError):
        get_image({"url": "http://x/image/Garage", "auth": "none"})


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
