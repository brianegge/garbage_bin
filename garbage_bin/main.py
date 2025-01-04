#!/usr/bin/env python3
"""monitor garage camera in loop"""

import configparser
import json
import logging
import signal
import sys
import time

import paho.mqtt.client as paho
import sdnotify
from PIL import UnidentifiedImageError
from ultralytics import YOLO

from garbage_bin.detect import detectframe, get_image, sanitize, save
from garbage_bin.device import Device

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()

RUNNING = True


class GracefulKiller:
    """
    A class to handle graceful termination of a program.

    Attributes:
    -----------
    kill_now : bool
        A flag to indicate if the program should terminate.

    Methods:
    --------
    __init__():
        Initializes the signal handlers for SIGABRT, SIGINT, and SIGTERM.

    exit_gracefully(*args):
        Sets the kill_now flag to True to indicate that the program should terminate.
    """

    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGABRT, signal.SIG_DFL)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


def on_publish(client, userdata, mid, reason_codes, properties):
    log.info(f"on_publish({userdata},{mid})")


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    log.info(f"mqtt connected: {reason_code}")
    client.publish("garagecam/status", "online", retain=True)


def on_disconnect(client, userdata, flags, reason_code, properties):
    log.info(f"mqtt disconnected reason: {reason_code}")
    global RUNNING
    RUNNING = False


def on_message(mqtt_client, obj, msg):
    log.info("on_message()")


def get_section(config, section):
    """
    Retrieve a section from a configuration object and validate its existence.

    Args:
        config: A configparser-like object containing configuration sections
        section (str): The name of the section to retrieve

    Returns:
        dict-like object: The configuration section if it exists

    Raises:
        ValueError: If the specified section does not exist in the config

    Ensure that the specified section is present in the config.
    """
    if not config.has_section(section):
        raise ValueError(f"Missing required section: {section}")
    return config[section]


def main():
    sd = sdnotify.SystemdNotifier()
    sd.notify("STATUS=Loading")
    model = YOLO("best.pt")  # pretrained YOLOv8n model
    config = configparser.ConfigParser()
    config.read("config.ini")
    mqtt_config = get_section(config, "mqtt")
    lwt = "garagecam/status"
    mqtt_client = paho.Client(paho.CallbackAPIVersion.VERSION2, "garage-cam")
    mqtt_client.will_set(lwt, "offline", retain=True)
    mqtt_client.enable_logger(logger=log)
    mqtt_client.on_publish = on_publish
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.username_pw_set(mqtt_config["user"], mqtt_config["password"])
    log.info(
        "Connecting to MQTT broker at %s:%s", mqtt_config["host"], mqtt_config["port"]
    )
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
    while RUNNING and not killer.kill_now:
        try:
            start = time.time()
            objects, img = detectframe(model, get_image(config["camera"]))
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
    sd.notify("STATUS=Gracefull Exit")


if __name__ == "__main__":
    main()
