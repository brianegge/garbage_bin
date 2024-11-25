#!/usr/bin/env python3
"""monitor garage camera in loop"""

import configparser
import faulthandler
import json
import logging
import signal
import sys
import time

import paho.mqtt.client as paho
import sdnotify
from PIL import UnidentifiedImageError
from ultralytics import YOLO

from garbage_bin.detect import detectframe, sanitize, save
from garbage_bin.device import Device

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()

model = None

running = True


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGABRT, self.handle_sigabrt)

    def exit_gracefully(self, *args):
        self.kill_now = True

    def handle_sigabrt(self, signum, frame):
        print("SIGABRT received")
        faulthandler.dump_traceback()


def on_publish(client, userdata, mid):
    log.info(f"on_publish({userdata},{mid})")


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    log.info("mqtt connected")
    client.publish("garagecam/status", "online", retain=True)


def on_disconnect(client, userdata, rc):
    log.info("mqtt disconnected reason  " + str(rc))
    global running
    running = False


def on_message(self, mqtt_client, obj, msg):
    log.info("on_message()")


def main():
    sd = sdnotify.SystemdNotifier()
    sd.notify("STATUS=Loading")
    model = YOLO("best.pt")  # pretrained YOLOv8n model
    config = configparser.ConfigParser()
    config.read("config.txt")
    mqtt_config = config["mqtt"]
    lwt = "garagecam/status"
    mqtt_client = paho.Client("garage-cam")
    mqtt_client.will_set(lwt, "offline", retain=True)
    mqtt_client.enable_logger(logger=log)
    mqtt_client.on_publish = on_publish
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.username_pw_set(mqtt_config["user"], mqtt_config["password"])
    mqtt_client.connect(mqtt_config["host"], int(mqtt_config["port"]))
    mqtt_client.subscribe("test")  # get on connect messages
    mqtt_client.loop_start()
    devices = list(
        map(lambda name: Device(name), ["Honda Civic", "Honda CR-V", "Garbage Bin"]),
    )
    for device in devices:
        j = {
            "name": device.name,
            "state_topic": f"{device.hass_name}/state",
            "device_class": "presence",
            "uniq_id": f"garagecam-{device.hass_name}",
            "availability_topic": lwt,
        }
        mqtt_client.publish(
            f"homeassistant/binary_sensor/{device.hass_name}/config",
            json.dumps(j),
            retain=True,
        )

    # curl -X GET -H "Authorization: Bearer config['hass']['token'] -H "Content-Type: application/json" http://homeassistant.home:8123/api/states/binary_sensor.garbage_bin_ha | python -m json.tool
    sd.notify("READY=1")
    sd.notify("STATUS=Running")
    killer = GracefulKiller()
    while running and not killer.kill_now:
        try:
            start = time.time()
            objects, img = detectframe(model, config["camera"])
            sd.notify("WATCHDOG=1")
            if "person" in objects and objects["person"] > 0.6:
                log.info("Skipping while person is in garage")
                continue
            if objects["something"] < 0.1:
                log.info("Nothing is in garage")
                # continue
            for device in devices:
                command = None
                if device.hass_name in objects:
                    command = device.update(objects[device.hass_name])
                else:
                    command = device.update(0.0)
                if command is not None:
                    save(config["file"]["path"], img, sanitize(objects))
                    mqtt_client.publish(
                        f"{device.hass_name}/state",
                        command.upper(),
                        retain=True,
                    )
            delay = 15.0 - (time.time() - start)
            if delay > 0.0:
                time.sleep(delay)
        except UnidentifiedImageError:
            pass
        except KeyboardInterrupt:
            break
    publish_result = mqtt_client.publish(lwt, payload="offline", retain=True)
    publish_result.wait_for_publish()
    mqtt_client.disconnect()  # disconnect gracefully
    mqtt_client.loop_stop()  # stops network loop
    log.info("Gracefully exiting")


if __name__ == "__main__":
    main()
