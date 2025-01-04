import configparser

import pytest

from garbage_bin.main import get_section


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
