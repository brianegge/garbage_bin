#!/usr/bin/python3
"""
  monitor garage camera in loop
"""
import configparser
import json
import logging
import signal
import sys
import time
from pprint import pprint

import paho.mqtt.client as paho
import sdnotify
from PIL import UnidentifiedImageError
from systemd import journal

from detect import detectframe, sanitize, save
from ultralytics import YOLO

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()
# log.addHandler(journal.JournalHandler())
# log.setLevel(logging.DEBUG)
# log.propagate = False

model = None

running = True


class Device(object):
    """
    hold object state and ST reference
    """

    def __init__(self, name):
        self.name = name
        self.ssd_name = name.lower().replace("-", "")
        self.hass_name = self.ssd_name.replace(" ", "_")
        self.value = 0.8
        self.status = "unknown"

    def update(self, value):
        old_value = self.value
        self.value = old_value * 0.7 + value * 0.3
        if self.value < 0.6 and self.status != "off":
            log.info(
                "{} departed {:.3f}+{:.3f}=>{:.3f}".format(
                    self.name, value, old_value, self.value
                )
            )
            self.status = "off"
            return "off"
        elif self.value > 0.9 and self.status != "on":
            log.info(
                "{} arrived {:.3f}+{:.3f}=>{:.3f}".format(
                    self.name, value, old_value, self.value
                )
            )
            self.status = "on"
            return "on"
        elif abs(self.value - old_value) > 0.0005:
            log.info(
                "{} updated {:.3f}+{:.3f}=>{:.3f}".format(
                    self.name, value, old_value, self.value
                )
            )
        return None


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


def on_publish(client, userdata, mid):
    log.info("on_publish({},{})".format(userdata, mid))


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
    lwt = "garagecam/status"
    mqtt_client = paho.Client("garage-cam")
    mqtt_client.will_set(lwt, "offline", retain=True)
    mqtt_client.enable_logger(logger=log)
    mqtt_client.on_publish = on_publish
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.connect("mqtt.home", 1883)
    mqtt_client.subscribe("test")  # get on connect messages
    mqtt_client.loop_start()
    devices = list(
        map(lambda name: Device(name), ["Honda Civic", "Honda CR-V", "Garbage Bin"])
    )
    for device in devices:
        j = {
            "name": device.name,
            "state_topic": "{}/state".format(device.hass_name),
            "device_class": "presence",
            "uniq_id": "garagecam-{}".format(device.hass_name),
            "availability_topic": lwt,
        }
        mqtt_client.publish(
            "homeassistant/binary_sensor/{}/config".format(device.hass_name),
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
            objects, img = detectframe(model)
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
                if not command is None:
                    # st.set_switch_value(device.name,command)
                    save(img, sanitize(objects))
                    # if command == 'on':
                    #    command = 'present'
                    # elif command == 'off':
                    #    command = 'not_present'
                    mqtt_client.publish(
                        "{}/state".format(device.hass_name),
                        command.upper(),
                        retain=True,
                    )
            delay = 15.0 - (time.time() - start)
            if delay > 0.0:
                # mqtt_client.loop(delay)
                time.sleep(delay)
        except UnidentifiedImageError:
            pass
        except KeyboardInterrupt:
            break
    publish_result = mqtt_client.publish(lwt, payload = "offline", retain = True)
    publish_result.wait_for_publish()
    mqtt_client.disconnect()  # disconnect gracefully
    mqtt_client.loop_stop()  # stops network loop
    log.info("Gracefully exiting")


if __name__ == "__main__":
    main()
