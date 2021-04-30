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
    print('Sigaction!')


def camera_setup_all(cameras, engines, labels):
    disabled_list = []
    for name, settings in cameras.items():
        camera = None
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

            camera = Camera(name, settings["camera_url"], settings["camera_snapshot"], settings["width"], settings["height"])
            camera.open()
            settings["camera"] = camera
        except:
            print('Setup camera: %s FAILED' % name)
            if camera:
                camera.close()
            pass # Close all ....

    for key in disabled_list:
        del cameras[key]


def camera_start_all(cameras):
    for name, settings in cameras.items():
        camera = settings["camera"]
        if camera.is_open():
            try:
                print('Try start camera: %s' % camera.camera_name)
                camera.start()
            except Exception as e:
                print('Camera start exception: %s' % (e))
                camera.close()

    for name, settings in cameras.items():
        camera = settings["camera"]
        if camera.is_alive():
            print('Alive: %s' % camera.camera_name)
        else:
            print('NOT Alive: %s' % camera.camera_name)


def camera_process_all(cameras, mqtt):
    for name, settings in cameras.items():
        camera = settings["camera"]
        detector = settings["detector"]
        if camera.is_open():
            print('\nProcessing camera: %s' % name)
            # Classify the latest camera image and post on mqtt bus
            try:
                start_ms = time.time()

                print('Detect : %s' % name)
                img = camera.get_img()
                detections = detector.process_img(start_ms, tpu_config["confidence"], img)

                # Publish all detections (like "person, 81%")
                for detection in detections:
                    print('Detected: %s' % str(detection))
                    mqtt.publish(settings["mqtt_topic_detection"], detection)

                #cv2.imshow('Detected Objects', camera.get_img())
                png = camera.get_png()
                if png is not None:
                    mqtt.publish(settings["mqtt_topic_image"], png)

            except Exception as e:
                print('Exception: %s' % (e))
                continue
        else:
            print('Reopen camera: %s %s' % (name, settings["camera_url"]))
            camera.open()


def main():
    global do_loop
    signal.signal(signal.SIGINT, sig_handler)
    print('Starting program')


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
    print("Connect to mqtt")
    try:
        # Will throw on mqtt host error
        mqtt = mqtt_client(mqtt_config)
    except:
        return

    print("Setup all cameras")
    camera_setup_all(cameras, engines, labels)

    # Start all camera threads
    print("Start all cameras")
    camera_start_all(cameras)

    # Process images from the cameras
    print("Process all cameras")
    while do_loop:
        # Pull latest camera image and do detection on it
        camera_process_all(cameras, mqtt)
        # Sleep to not flood the mqtt bus
        if SLEEP_TIMER:
            time.sleep(SLEEP_TIMER)

    print("Close all cameras")
    for name, settings in cameras.items():
        try:
            camera = settings["camera"]
            camera.close()
        except:
           pass
    for name, settings in cameras.items():
        try:
            camera = settings["camera"]
            camera.join()
        except:
           pass

    print('Disconnect mqtt bus')
    mqtt.disconnect()

    #print('cv2 end')
    #cv2.destroyAllWindows()

    print('End of program')
    exit()

if __name__ == '__main__':
    main()
