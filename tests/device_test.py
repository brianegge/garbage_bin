from garbage_bin.device import Device


def test_device():
    d = Device("car")
    assert d.update(1) is None
    assert d.status == "unknown"
    assert d.value == 0.8599999999999999

    assert d.update(1) == "on"
    assert d.status == "on"
    assert d.value == 0.9019999999999999

    assert d.update(0) is None
    assert d.status == "on"
    assert d.value == 0.6313999999999999

    assert d.update(0) == "off"
    assert d.status == "off"
    assert d.value == 0.4419799999999999

    assert d.update(0) is None
    assert d.status == "off"
    assert d.value == 0.3093859999999999
