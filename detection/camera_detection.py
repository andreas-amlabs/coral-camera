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


# The local (hidden) configuration
# Contains e.g.
#SLEEP_TIMER = 5
#camera_list = [
#   {
#       "name": "Camera name",
#       "camera_url": "rtsp://user:pass@1.2.3.4:554/Streaming/Channels/102",
#       "camera_snapshot": "http://user:pass@1.2.3.4:554/snapshot.cgi",
#       "width": WIDTH,
#       "height": HEIGHT,
#       "mqtt_topic_image": "a/camera/topic"
#       "mqtt_topic_detection": "a/detection/topic"
#   }]
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


class Camera:
    camera = None
    rtsp_url = ""
    http_snapshot = ""
    img_width = 0
    img_height = 0
    img = None

    def __init__(self,
                 camera_url,
                 camera_snapshot,
                 camera_width,
                 camera_height):
        self.rtsp_url = camera_url
        self.http_snapshot = camera_snapshot
        self.width = camera_width
        self.height = camera_height

    def open(self):
        self.camera = cv2.VideoCapture(self.rtsp_url)
        self.camera.set(3, self.width)
        self.camera.set(4, self.height)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        #self.camera.set(cv2.CV_CAP_PROP_FPS, 10)
        self.camera.set(cv2.CAP_PROP_POS_AVI_RATIO, 1)

    def close(self):
        self.camera.release()

    def is_open(self):
        return self.camera.isOpened()

    def grab(self):
        return self.camera.grab()

    def retrieve(self):
        self.ret, self.img = self.camera.retrieve()
        return self.ret

    def read(self):
        self.ret, self.img = self.camera.read()
        return self.ret

    def get_img(self):
        return self.img

    def get_png(self):
        return cv2.imencode('.png', self.img)[1].tostring()

    def snapshot(self):
        self.img = None
        r = requests.get(self.http_snapshot)
        self.img = Image.open(BytesIO(r.content))


class Detector:
    def __init__(self, engine, height, labels):
        self.engine = engine
        self.elapsed_ms = 0
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.bottomLeftCornerOfText = (10, height-10)
        self.fontScale = 1
        self.fontColor = (255, 255, 255)  # white
        self.boxColor = (0, 0, 255)   # RED?
        self.boxLineWidth = 1
        self.lineType = 2
        self.labels = labels
    
    def process_img(self, start_ms, img):
        detections = []
        input = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # convert to RGB color space
        img_pil = Image.fromarray(input)
        results = self.engine.detect_with_image(img_pil, threshold=tpu_config["confidence"], keep_aspect_ratio=True, relative_coord=False, top_k=5)
        end_tf_ms = time.time()
        elapsed_tf_ms = end_tf_ms - start_ms
                
        for obj in results:
            #print("%s, %.0f%% %.2fms" % (self.labels[obj.label_id], obj.score *100, elapsed_tf_ms * 1000))
            box = obj.bounding_box
            coord_top_left = (int(box[0][0]), int(box[0][1]))
            coord_bottom_right = (int(box[1][0]), int(box[1][1]))
            cv2.rectangle(img, coord_top_left, coord_bottom_right, self.boxColor, self.boxLineWidth)
            annotate_text = "%s, %.0f%%" % (self.labels[obj.label_id], obj.score * 100)
            detections.append(annotate_text)
            coord_top_left = (coord_top_left[0], coord_top_left[1]+15)
            cv2.putText(img, annotate_text, coord_top_left, self.font, self.fontScale, self.boxColor, self.lineType )

        # Print Frame rate info
        self.elapsed_ms = time.time() - start_ms
        annotate_text = "%.2f FPS, %.2fms total, %.2fms in tf " % (1.0 / self.elapsed_ms, self.elapsed_ms*1000, elapsed_tf_ms*1000)
        #print('%s: %s' % (datetime.datetime.now(), annotate_text))
        cv2.putText(img, annotate_text, self.bottomLeftCornerOfText, self.font, self.fontScale, self.fontColor, self.lineType)

        # Return the list of detections so that they
        # may eg. be published on mqtt bus
        return detections


def setup_all(camera_list, engines, labels):
    index = 0
    for camera_dict in camera_list:
        try:
            print('Setup camera: %s' % camera_dict["name"])

            camera_dict["mqtt_topic_image"] += camera_dict["name"]
            camera_dict["mqtt_topic_detection"] += camera_dict["name"]

            # To get the text correctly placed in the detection,
            # create One detection per camera
            # Setup the detector
            camera_dict["detector"] = Detector(engines[camera_dict["model"]], camera_dict["height"], labels)

            camera = Camera(camera_dict["camera_url"], camera_dict["camera_snapshot"], camera_dict["width"], camera_dict["height"])
            camera_dict["camera"] = camera
            camera.open()
        except:
            print('Setup camera: %s FAILED' % camera_dict["name"])
            camera.close()
            pass # Close all ....
        index += 1


def grab_all(camera_list):
    global do_loop
    print('\nGrabbing cameras')
    for camera_dict in camera_list:
        if not do_loop:
            break
        camera = camera_dict["camera"]
        detector = camera_dict["detector"]
        if camera.is_open():
            print('Grabbing camera: %s' % (camera_dict["name"]))
            try:
                camera.grab()
            except Exception as e:
                print('Camera grab exception: %s' % (e))
                camera.close()
                continue


def process_all(camera_list, mqtt):
    global do_loop
    for camera_dict in camera_list:
        if not do_loop:
            break
        camera = camera_dict["camera"]
        detector = camera_dict["detector"]
        if camera.is_open():
            print('\nProcessing camera: %s' % (camera_dict["name"]))
            # Pull an image, classify it and post on mqtt bus
            try:
                start_ms = time.time()
                if camera.retrieve() == False:
                    print('Failed to get image from camera: %s %s' % (camera_dict["name"], camera_dict["camera_url"]))
                    camera.close()
                    continue

                #print('Snapshot: %s' % (camera_dict["name"]))
                #camera.snapshot()

                print('Detect : %s' % (camera_dict["name"]))
                detections = detector.process_img(start_ms, camera.get_img())

                # Publish all detections (like "person, 81%")
                for detection in detections:
                    print('Detected: %s' % str(detection))
                    mqtt.publish(camera_dict["mqtt_topic_detection"], detection)

                #cv2.imshow('Detected Objects', camera.get_img())
                mqtt.publish(camera_dict["mqtt_topic_image"], camera.get_png())

            except Exception as e:
                print('Exception: %s' % (e))
                continue
        else:
            print('Reopen camera: %s %s' % (camera_dict["name"], camera_dict["camera_url"]))
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

    setup_all(camera_list, engines, labels)

    while do_loop:
        grab_all(camera_list)
        process_all(camera_list, mqtt)
        #if SLEEP_TIMER:
            #time.sleep(SLEEP_TIMER)

    for camera_dict in camera_list:
        try:
            camera = camera_dict["camera"]
            camera.close()
        except:
           pass

    cv2.destroyAllWindows()
    print('End of program')

if __name__ == '__main__':
    main()
