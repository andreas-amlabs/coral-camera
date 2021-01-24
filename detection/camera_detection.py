"""
    Test code based on coco object detection.py example

    This code has been modified to post detections on
    an mqtt bus
"""
import argparse
import time
import signal

import numpy as np
import os
import datetime
import requests
from io import BytesIO

import edgetpu.detection.engine
import cv2
from PIL import Image
from mqtt_client import mqtt_client
from datetime import datetime

from Camera import *
from Detector import *


# The local (hidden) configuration
# Contains e.g.
#SLEEP_TIMER = 5
#cameras = {
#   "Camera name":
#   {
#       "model": MODEL,
#       "enabled": True,
#       "camera_url": "rtsp://user:pass@1.2.3.4:554/Streaming/Channels/102",
#       "camera_snapshot": "http://user:pass@1.2.3.4:554/snapshot.cgi",
#       "width": WIDTH,
#       "height": HEIGHT,
#       "mqtt_topic_image": "a/camera/topic"
#       "mqtt_topic_detection": "a/detection/topic"
#   }}
#tpu_config = {
#   "confidence": 0.50,
#   "model": "ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite",
#   "labels": "coco_labels.txt"
#}
#   mqtt_config = {
#       "name": "name",
#       "host": "mqtt.local",
#       "username": "user",
#       "password": "pass",
#   }
from local_config import *


do_loop = True


# Abort looping on Signal
def sig_handler(signum, frame):
    global do_loop
    do_loop = False


def setup_all(cameras, engines, labels):
    disabled_list = []
    for name, settings in cameras.items():
        try:
            print('Setup camera: %s' % name)
            if not settings["enabled"]:
                print('Camera: %s is disabled' % name)
                disabled_list.append(name)
                continue

            settings["mqtt_topic_image"] += name
            settings["mqtt_topic_detection"] += name

            # To get the text correctly placed in the detection,
            # create One detection per camera
            # Setup the detector
            settings["detector"] = Detector(engines[settings["model"]], settings["height"], labels)

            camera = Camera(settings["camera_url"], settings["camera_snapshot"], settings["width"], settings["height"])
            settings["camera"] = camera
            camera.open()
        except:
            print('Setup camera: %s FAILED' % name)
            camera.close()
            pass # Close all ....

    for key in disabled_list:
        del cameras[key]


def grab_all(cameras):
    global do_loop
    print('\nGrabbing cameras')
    for name, settings in cameras.items():
        if not do_loop:
            break
        camera = settings["camera"]
        detector = settings["detector"]
        if camera.is_open():
            print('Grabbing camera: %s' % name)
            try:
                camera.grab()
            except Exception as e:
                print('Camera grab exception: %s' % (e))
                camera.close()
                continue


def process_all(cameras, mqtt):
    global do_loop
    for name, settings in cameras.items():
        if not do_loop:
            break
        camera = settings["camera"]
        detector = settings["detector"]
        if camera.is_open():
            print('\nProcessing camera: %s' % name)
            # Pull an image, classify it and post on mqtt bus
            try:
                start_ms = time.time()
                if camera.retrieve() == False:
                    print('Failed to get image from camera: %s %s' % (name, settings["camera_url"]))
                    camera.close()
                    continue

                #print('Snapshot: %s' % name)
                #camera.snapshot()

                print('Detect : %s' % name)
                detections = detector.process_img(start_ms, tpu_config["confidence"], camera.get_img())

                # Publish all detections (like "person, 81%")
                for detection in detections:
                    print('Detected: %s' % str(detection))
                    mqtt.publish(settings["mqtt_topic_detection"], detection)

                #cv2.imshow('Detected Objects', camera.get_img())
                mqtt.publish(settings["mqtt_topic_image"], camera.get_png())

            except Exception as e:
                print('Exception: %s' % (e))
                continue
        else:
            print('Reopen camera: %s %s' % (name, settings["camera_url"]))
            camera.open()


def main():
    global do_loop
    #print('Starting program')
    print('Starting pr')
    signal.signal(signal.SIGINT, sig_handler)


    # Init Coral edge tpu
    engines = {}
    print('Load engines')
    for name, item in tpu_config["models"].items():
        print("Load engine name:%s model:%s" % (name, item["model"]))
        engines[name] = edgetpu.detection.engine.DetectionEngine(item["model"])

        # Read labels
        print("Read labels %s" % (item["labels"]))
        with open(item["labels"], 'r') as f:
            pairs = (l.strip().split(maxsplit=1) for l in f.readlines())
            labels = dict((int(k), v) for k, v in pairs)

    # Connect to mqtt server
    try:
        # Will throw on mqtt host error
        mqtt = mqtt_client(mqtt_config)
    except:
        return

    setup_all(cameras, engines, labels)

    while do_loop:
        grab_all(cameras)
        process_all(cameras, mqtt)
        #if SLEEP_TIMER:
            #time.sleep(SLEEP_TIMER)

    for settings in cameras:
        try:
            camera = camera_dict["camera"]
            camera.close()
        except:
           pass

    cv2.destroyAllWindows()
    print('End of program')

if __name__ == '__main__':
    main()
