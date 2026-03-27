import configparser

import pytest

from garbage_bin.main import (
    connect_mqtt,
    get_device_info,
    get_health_status,
    get_section,
    get_version,
    graceful_shutdown,
    load_config,
    on_connect,
    on_disconnect,
    on_message,
    publish_discovery,
)


def test_get_section_exists():
    config = configparser.ConfigParser()
    config.add_section("mqtt")
    config.set("mqtt", "host", "localhost")
    section = get_section(config, "mqtt")
    assert section["host"] == "localhost"


def test_get_section_missing():
    config = configparser.ConfigParser()
    with pytest.raises(ValueError, match="Missing required section: mqtt"):
        get_section(config, "mqtt")


def test_load_config_file_exists(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data="[mqtt]\nhost=localhost"))
    config = load_config()
    assert config.has_section("mqtt")
    assert config.get("mqtt", "host") == "localhost"


def test_load_config_empty_file(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data=""))
    config = load_config()
    assert len(config.sections()) == 0


def test_load_config_multiple_sections(mocker):
    mocker.patch(
        "builtins.open",
        mocker.mock_open(read_data="[mqtt]\nhost=localhost\n[http]\nport=8080"),
    )
    config = load_config()
    assert config.has_section("mqtt")
    assert config.has_section("http")
    assert config.get("http", "port") == "8080"


def test_on_connect_publishes_status_and_process_state(mocker):
    mocker.patch("garbage_bin.main.get_version", return_value="v1.0.0")
    client = mocker.MagicMock()
    on_connect(client, None, None, 0, None)
    client.publish.assert_any_call("garagecam/status", "online", retain=True)
    client.publish.assert_any_call("garagecam/process/state", "running", retain=True)
    client.publish.assert_any_call("garagecam/version/state", "v1.0.0", retain=True)


def test_on_disconnect_clean(mocker, caplog):
    """Clean disconnect (reason_code 0) logs at info level."""
    import logging

    with caplog.at_level(logging.INFO):
        on_disconnect(mocker.MagicMock(), None, None, 0, None)
    assert "mqtt disconnected (clean)" in caplog.text


def test_on_disconnect_unexpected(mocker, caplog):
    """Unexpected disconnect logs a warning and does not kill the process."""
    import logging

    with caplog.at_level(logging.WARNING):
        on_disconnect(mocker.MagicMock(), None, None, 7, None)
    assert "auto-reconnect" in caplog.text


def test_graceful_shutdown_publishes_and_disconnects(mocker):
    client = mocker.MagicMock()
    sd = mocker.MagicMock()
    graceful_shutdown(client, "garagecam/status", sd)
    client.publish.assert_any_call("garagecam/process/state", "stopped", retain=True)
    client.publish.assert_any_call("garagecam/status", payload="offline", retain=True)
    client.disconnect.assert_called_once()
    client.loop_stop.assert_called_once()
    sd.notify.assert_called_with("STATUS=Graceful Exit")


def test_graceful_shutdown_handles_publish_failure(mocker, caplog):
    """Shutdown completes even when MQTT publish fails."""
    import logging

    client = mocker.MagicMock()
    client.publish.side_effect = RuntimeError("not connected")
    sd = mocker.MagicMock()
    with caplog.at_level(logging.WARNING):
        graceful_shutdown(client, "garagecam/status", sd)
    assert "Could not publish offline status" in caplog.text
    client.disconnect.assert_called_once()
    client.loop_stop.assert_called_once()


def test_connect_mqtt_succeeds_first_try(mocker):
    client = mocker.MagicMock()
    connect_mqtt(client, "localhost", 1883)
    client.connect.assert_called_once_with("localhost", 1883)


def test_connect_mqtt_retries_on_failure(mocker):
    """Retries connection on OSError and succeeds on later attempt."""
    mocker.patch("garbage_bin.main.time.sleep")
    client = mocker.MagicMock()
    client.connect.side_effect = [OSError("refused"), OSError("refused"), None]
    connect_mqtt(client, "localhost", 1883)
    assert client.connect.call_count == 3


def test_connect_mqtt_raises_after_max_retries(mocker):
    client = mocker.MagicMock()
    client.connect.side_effect = OSError("refused")
    mocker.patch("garbage_bin.main.time.sleep")
    with pytest.raises(OSError, match="refused"):
        connect_mqtt(client, "localhost", 1883, max_retries=3)
    assert client.connect.call_count == 3


def test_connect_mqtt_exponential_backoff(mocker):
    """Verify sleep delays double each retry."""
    sleep_mock = mocker.patch("garbage_bin.main.time.sleep")
    client = mocker.MagicMock()
    client.connect.side_effect = [OSError("fail")] * 3 + [None]
    connect_mqtt(client, "localhost", 1883, max_retries=4, initial_delay=2)
    assert sleep_mock.call_args_list == [
        mocker.call(2),
        mocker.call(4),
        mocker.call(8),
    ]


def test_get_version_from_file(tmp_path, mocker):
    version_file = tmp_path / "GIT_VERSION_TAG.txt"
    version_file.write_text("v1.2.3\n")
    mocker.patch("garbage_bin.main.Path", return_value=version_file)
    assert get_version() == "v1.2.3"


def test_get_version_fallback(tmp_path, mocker):
    mocker.patch("garbage_bin.main.Path", return_value=tmp_path / "nonexistent.txt")
    assert get_version() == "dev"


def test_get_device_info(mocker):
    mocker.patch("garbage_bin.main.get_version", return_value="v1.0.0")
    info = get_device_info()
    assert info["identifiers"] == ["garagecam"]
    assert info["name"] == "Garage Camera"
    assert info["sw_version"] == "v1.0.0"


def test_get_health_status_healthy():
    assert get_health_status(200, 100, True) == "healthy"


def test_get_health_status_camera_error():
    assert get_health_status(200, 100, False) == "camera_error"


def test_get_health_status_degraded_memory():
    assert get_health_status(600, 100, True) == "degraded"


def test_get_health_status_degraded_inference():
    assert get_health_status(200, 400, True) == "degraded"


def test_get_health_status_camera_error_takes_priority():
    """Camera error takes priority over degraded metrics."""
    assert get_health_status(600, 400, False) == "camera_error"


def test_publish_discovery_publishes_all_entities(mocker):
    """publish_discovery sends discovery configs for all devices plus fixed sensors."""
    mocker.patch("garbage_bin.main.get_version", return_value="v1.0.0")
    client = mocker.MagicMock()
    device1 = mocker.MagicMock()
    device1.name = "Honda Civic"
    device1.hass_name = "honda_civic"
    device2 = mocker.MagicMock()
    device2.name = "Garbage Bin"
    device2.hass_name = "garbage_bin"
    publish_discovery(client, [device1, device2], "garagecam/status")
    topics = [call.args[0] for call in client.publish.call_args_list]
    assert "homeassistant/binary_sensor/honda_civic/config" in topics
    assert "homeassistant/binary_sensor/garbage_bin/config" in topics
    assert "homeassistant/binary_sensor/garagecam-nfs_storage/config" in topics
    assert "homeassistant/sensor/garagecam-process/config" in topics


def test_on_message_ha_online_republishes(mocker):
    """on_message re-publishes discovery when HA comes online."""
    mocker.patch("garbage_bin.main.get_version", return_value="v1.0.0")
    mock_publish = mocker.patch("garbage_bin.main.publish_discovery")
    client = mocker.MagicMock()
    devices = [mocker.MagicMock()]
    userdata = {"devices": devices, "lwt": "garagecam/status"}
    msg = mocker.MagicMock()
    msg.topic = "homeassistant/status"
    msg.payload.decode.return_value = "online"
    on_message(client, userdata, msg)
    mock_publish.assert_called_once_with(client, devices, "garagecam/status")


def test_on_message_ignores_other_topics(mocker):
    """on_message does not republish for unrelated messages."""
    mock_publish = mocker.patch("garbage_bin.main.publish_discovery")
    client = mocker.MagicMock()
    msg = mocker.MagicMock()
    msg.topic = "some/other/topic"
    msg.payload.decode.return_value = "hello"
    on_message(client, None, msg)
    mock_publish.assert_not_called()


def test_on_message_ignores_ha_offline(mocker):
    """on_message does not republish when HA goes offline."""
    mock_publish = mocker.patch("garbage_bin.main.publish_discovery")
    client = mocker.MagicMock()
    msg = mocker.MagicMock()
    msg.topic = "homeassistant/status"
    msg.payload.decode.return_value = "offline"
    on_message(client, None, msg)
    mock_publish.assert_not_called()
