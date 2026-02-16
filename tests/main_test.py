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


def test_on_disconnect_sets_running_false(mocker):
    import garbage_bin.main as main_module

    main_module.RUNNING = True
    on_disconnect(mocker.MagicMock(), None, None, 0, None)
    assert main_module.RUNNING is False
