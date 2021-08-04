import requests
from pprint import pprint
from urllib.parse import quote

class SmartThings(object):
    """ interface with SmartThings
    """

    def __init__(self, config):
        self.config = config['smartthings']
        self.headers = {"Authorization": "Bearer {}".format(self.config['token'])}
        response = requests.get('https://api.smartthings.com/v1/scenes', headers=self.headers)
        self.scenes = response.json()['items']
        response = requests.get('https://api.smartthings.com/v1/devices', headers=self.headers)
        self.devices = response.json()['items']
        print("SmartThings started with {} scenes and {} devices".format(len(self.scenes),len(self.devices)))

    def set_st_scene(self, scene):
        #curl -H "Authorization: Bearer <>" https://api.smartthings.com/v1/scenes | python -m json.tool
        for s in self.scenes:
            if s['sceneName'] == scene:
                print("Setting scene={sceneName}".format(**s))
                r = requests.post('https://api.smartthings.com/v1/scenes/{sceneId}/execute'.format(**s), headers=self.headers)
                return r.content.decode("utf-8")
        print("Failed to find scene={}".format(scene))

    def open_garage_door(self):
        if self.get_contactSensor_value('Garage Door Right') == "closed":
            device = self.get_device('Garage Opener Right')
            json=[{"component":"main","capability":"momentary","command":"push", "arguments":[]}]
            r = requests.post('https://api.smartthings.com/v1/devices/{deviceId}/commands'.format(**device), headers=self.headers, json=json)
            return r.content.decode("utf-8")

    def crack_garage_door(self):
        r = requests.get('https://graph-na04-useast2.api.smartthings.com/api/token/0f145ac7-a135-48ad-969d-a7287bd38a26/smartapps/installations/0aea3b0d-96de-461c-99a8-ef53a3fb6384/execute/:e3155f82b07d3c384bab97d51e9b841e:')
        print(r.text)
        if r.json()['result'] != "OK":
            print("Failed to crack open garage door")
            print(r.text)

    def deer_alert(self):
        print("Deer alert!")
        # invoke webcore piston
        r = requests.get(self.config['deer_alert'])
        if r.json()['result'] != "OK":
            print("Failed to alert for deer")
            print(r.text)

    def get_device(self, name):
        for device in self.devices:
            if device['label'] == name:
                return device
        raise Exception("No such device \"{}\"".format(name))

    def get_contactSensor_value(self, sensor):
        device = self.get_device(sensor)
        response = requests.get('https://api.smartthings.com/v1/devices/{deviceId}/components/main/capabilities/contactSensor/status'.format(**device), headers=self.headers).json()
        return response['contact']['value']

    def get_switch_value(self, switch):
        device = self.get_device(switch)
        url = 'https://api.smartthings.com/v1/devices/{deviceId}/components/main/capabilities/switch/status'.format(**device)
        pprint(url)
        response = requests.get(url, headers=self.headers).json()
        pprint(response)
        return response['switch']['value'] == "on"

    def set_switch_value(self, switch, value):
        device = self.get_device(switch)
        json=[{"component":"main","capability":"switch","command":value, "arguments":[]}]
        r = requests.post('https://api.smartthings.com/v1/devices/{deviceId}/commands'.format(**device), headers=self.headers, json=json)
        return r.content.decode("utf-8")

    def should_notify_vehicle(self):
        return self.get_switch_value('Vehicle Detector')

    def should_notify_person(self):
        return self.get_switch_value('Person Detector')

    def echo_speaks(self, message):
        url = self.config['echo_speaks']
        print("Speaking {}".format(message))
        r = requests.get(url + quote(message))
        return r.content.decode("utf-8")

    def get_st_mode(self):
        r = requests.get('http://192.168.254.6:8282/mode')
        c = r.content.decode("utf-8")
        return c.lower()
    
    def suppress_notify_person(self):
        r = requests.get(self.config['suppress_notify_person'])
        c = r.content.decode("utf-8")
        print("Keep person notify suppressed={}".format(c))
        return r.content.decode("utf-8")

    def turn_on_outside_lights(self):
        r = requests.get(self.config['turn_on_outside_lights'])
        c = r.content.decode("utf-8")
        print("Turned on outside lights".format(c))
        return r.content.decode("utf-8")
