[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/brianegge/garbage_bin/badge)](https://scorecard.dev/viewer/?uri=github.com/brianegge/garbage_bin)
[![Coverage Status](https://coveralls.io/repos/github/brianegge/garbage_bin/badge.png?branch=master)](https://coveralls.io/github/brianegge/garbage_bin?branch=master)

This project is to detect which cars are in my garage as well as if the garbage bins are present. I use a simple object detection model along with an IP Camera in my garage. I publish the state as bianry sensors for use in HomeAssistant. The images used for training are here: https://app.roboflow.com/egge-public/garage/overview

The script uses a rolling average to determine if the object is present or absent, and also skips updating if it detects a person, as they may be obscuring something. I also trained it to recongize my toolbucket. This is a sort of sanity / calibration check. If it finds nothing in the scene, it's likely a system problem, so it shouldn't update the state of the objects.

<img width="779" alt="image" src="https://github.com/brianegge/garbage_bin/assets/175930/ee8b9e05-b508-479b-9ac7-670228d3a32f">

*Quick Start*

You need to create a config file which connects to the camera and MQTT broker.

```ini
[file]
# where to save the images
path=/mnt/capture

[camera]
user=admin
password=*****
host=garage-cam.home

[mqtt]
host=mqtt
port=1883
```

```bash
podman run -it --rm -v etc/config.ini:/app/config.ini brianegge/garbage_bin
```

Install service from source

```bash
$ cat /etc/systemd/system/garbage_bin_detector.service
[Unit]
Description=Image processor to find the garbage bin
After=network.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
User=egge
WorkingDirectory=/home/egge/garbage_bin/flask
ExecStart=/home/egge/garbage_bin/flask/simple.py

[Install]
WantedBy=multi-user.target
```
Install service via podman

```bash
cp podman-systemd.service ~/.config/systemd/user/container-garbage_bin.service
systemctl --user daemon-reload
systemctl --user enable container-garbage_bin.service
systemctl --user start container-garbage_bin.service

systemctl --user enable podman-auto-update.service
systemctl --user start podman-auto-update.service
```

Here is one of my automations, which closes my garage door after I leave:

```yaml
alias: Garage Close Civic departs
description: "Close left garage door after departure "
trigger:
  - platform: state
    entity_id:
      - person.brian
    to: not_home
    from: home
condition:
  - condition: state
    entity_id: binary_sensor.honda_civic
    state: "off"
  - condition: state
    entity_id: cover.garage_door_left
    state: open
action:
  - service: cover.close_cover
    target:
      entity_id:
        - cover.garage_door_left
    data: {}
  - wait_for_trigger:
      - platform: state
        entity_id:
          - cover.garage_door_left
        to: closed
    timeout: "60"
  - service: notify.mobile_app_brians_iphone_x
    data:
      message: Garage door left is {{ states('cover.garage_door_left') }}
      data:
        entity_id: camera.garage_cam
        url: /lovelace-mobile/garage/
mode: single
```

The arriving home automations are a bit more complicated, because I might be driving either car. If both cars are away, I'm driving the Civic. If the Civic is present, I'm driving the CRV.
