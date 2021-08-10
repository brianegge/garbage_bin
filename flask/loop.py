#!/usr/bin/python3
"""
  monitor garage camera in loop
"""
import logging
from utils.detect import detectframe2,sanitize,save
from utils.ssd2 import TfSSD2
import sdnotify
import json
import time
import configparser
from pprint import pprint
from PIL import UnidentifiedImageError
import paho.mqtt.client as paho


ssd = None

class Device(object):
    """
    hold object state and ST reference
    """
    def __init__(self, name):
        self.name = name
        self.ssd_name = name.lower().replace('-','')
        self.hass_name = self.ssd_name.replace(' ','_')
        self.value = 0.8
        self.status = 'unknown'

    def update(self, value):
        old_value = self.value
        self.value = old_value * 0.7 + value * 0.3
        if self.value < 0.6 and self.status != 'off':
            print("{} departed {:.3f}+{:.3f}=>{:.3f}".format(self.name, value, old_value, self.value), end=" ")
            self.status = 'off'
            return 'off'
        elif self.value > 0.9 and self.status != 'on':
            print("{} arrived {:.3f}+{:.3f}=>{:.3f}".format(self.name, value, old_value, self.value), end=" ")
            self.status = 'on'
            return 'on'
        else:
            print("{} updated {:.3f}+{:.3f}=>{:.3f}".format(self.name, value, old_value, self.value), end=" ")
            return None

def on_publish(client, userdata, mid):
    print("on_publish({},{})".format(userdata, mid))

def main():
    config = configparser.ConfigParser()
    config.read('config.txt')
    mqtt_client = paho.Client("garage-cam")
    mqtt_client.on_publish = on_publish
    mqtt_client.connect("mqtt.home",1883)
    mqtt_client.loop_start()
    devices = list(map(lambda name: Device(name), ['Honda Civic','Honda CR-V','Garbage Bin']))
    for device in devices:
        j = {
             "name":device.name,
             "state_topic":"{}/state".format(device.hass_name),
             "device_class": "presence",
             "uniq_id":"garagecam-{}".format(device.hass_name),
             }
        mqtt_client.publish("homeassistant/binary_sensor/{}/config".format(device.hass_name), json.dumps(j), retain=True)
        
    # curl -X GET -H "Authorization: Bearer config['hass']['token'] -H "Content-Type: application/json" http://homeassistant.home:8123/api/states/binary_sensor.garbage_bin_ha | python -m json.tool
    while True:
        try:
            start = time.time()
            objects, img = detectframe2(ssd)
            #pprint(objects)
            if 'person' in objects and float(objects['person']) > 0.6:
                print("Skipping while person is in garage")
                continue
            if max(objects.values()) < 0.1:
                print("Skipping because nothing is in garage")
                continue
            for device in devices:
                command = None
                if device.ssd_name in objects:
                    command = device.update(objects[device.ssd_name])
                else:
                    command = device.update(0.0)
                if not command is None:
                    #st.set_switch_value(device.name,command)
                    save(img, sanitize(objects))
                    #if command == 'on':
                    #    command = 'present'
                    #elif command == 'off':
                    #    command = 'not_present'
                    mqtt_client.publish("{}/state".format(device.hass_name), command.upper(), retain=True)
            print() # end line as above loop doesn't publish one
            delay = 15.0 - (time.time() - start)
            if delay > 0.0:
                #mqtt_client.loop(delay)
                time.sleep(delay)
        except UnidentifiedImageError:
            pass
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    print('loading model')
    ssd = TfSSD2('frozen_inference_graph', (300, 300))
    # warm up
    #pprint(detectframe2(ssd))
    #pprint(json.dumps(detectframe(ssd)).encode('utf-8'))
    n = sdnotify.SystemdNotifier()
    n.notify("READY=1")
    main()
