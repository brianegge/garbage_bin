import configparser

import pytest

from garbage_bin.main import get_section, load_config


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
