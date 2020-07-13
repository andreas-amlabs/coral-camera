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

    def no_motion(self):
        if self.client == None:
            return
        debug("publishing motion OFF");
        self.client.publish(self.mqtt_motion, '{"on":"OFF"}')

    def publish(self, mqtt_topic, detection_type, likelihood):
        if self.client == None:
            return
        debug("Publishing ", detection_type, likelihood)

        #if detection_type not in self.detects:
            #self.detects[detection_type] = 0
        #if self.detects[detection_type] + 10.0 < time.time():
            #self.detects[detection_type] = time.time()
            #debug("publish TTS")
            #self.client.publish(self.mqtt_tts, "There is a " + detection_type + " in the " + self.name)
            #debug("publish Motion")
            #self.client.publish(mqtt_topic, '{"on":"ON", "type":"' + detection_type + '"}')
            #if self.timer is not None:
                #self.timer.cancel()
            #debug("Setting up timer for 15 seconds")
            #self.timer = threading.Timer(15, self.no_motion)
            #self.timer.start()

    def publish(self, mqtt_topic, image):
        if self.client == None:
            return
        debug("Publishing image.")
        self.client.publish(mqtt_topic, image)

    def __del__(self):
        if self.client == None:
            return
        self.client.disconnect()
        self.client.loop_stop()

