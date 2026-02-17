import configparser

import pytest

from garbage_bin.main import get_section, load_config, on_connect, on_disconnect


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
    client = mocker.MagicMock()
    on_connect(client, None, None, 0, None)
    client.publish.assert_any_call("garagecam/status", "online", retain=True)
    client.publish.assert_any_call("garagecam/process/state", "running", retain=True)


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
