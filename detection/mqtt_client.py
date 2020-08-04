import paho.mqtt.client as mqttClient
import threading, time

debug_enable = 0
def debug(*arg):
    if debug_enable:
        print(arg)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        debug("Connected to broker:", rc)
    else:
        debug("Connection failed: ", rc)

class mqtt_client:
    client = None
    timer = None
    config = {}

    def __init__(self, config=None):
        if not config:
            config["name"] = "MQTT Name"
            config["host"] = "127.0.0.1"

        self.config = config

        self.client = mqttClient.Client(self.config["name"])
        self.client.on_connect = on_connect
        if self.config["username"] and self.config["password"]:
            self.client.username_pw_set(self.config["username"], self.config["password"])

        self.client.connect(self.config["host"])
        self.client.loop_start()

    def publish(self, mqtt_topic, payload):
        if self.client == None:
            return
        debug("Publishing payload.")
        self.client.publish(mqtt_topic, payload)

    def __del__(self):
        if self.client == None:
            return
        self.client.disconnect()
        self.client.loop_stop()

