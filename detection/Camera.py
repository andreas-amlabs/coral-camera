"""
    A camera representation
"""
import requests
import time
from threading import Thread, Lock
from io import BytesIO

import cv2


class Camera(Thread):
    camera = None
    camera_name = ""
    rtsp_url = ""
    http_snapshot = ""
    img_width = 0
    img_height = 0
    img = None
    lock = None
    do_run = False

    def __init__(self,
                 camera_name,
                 camera_url,
                 camera_snapshot,
                 camera_width,
                 camera_height):
        #super(Camera, self).__init__()
        Thread.__init__(self)
        print('New camera: %s' % camera_name)
        self.camera_name = camera_name
        self.rtsp_url = camera_url
        self.http_snapshot = camera_snapshot
        self.width = camera_width
        self.height = camera_height
        self.lock = Lock()

    def open(self):
        print('Open camera: %s' % self.camera_name)
        self.camera = cv2.VideoCapture(self.rtsp_url)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        self.camera.set(cv2.CAP_PROP_POS_AVI_RATIO, 1)
        #self.camera.set(cv2.CV_CAP_PROP_FPS, 1)
        self.do_run = True

    def close(self):
        print("Closing camera %s" % self.camera_name)
        self.do_run = False
        self.lock.acquire()
        self.img = None
        self.lock.release()
        if self.is_open():
            self.camera.release()

    def is_open(self):
        return self.camera.isOpened()

    def grab(self):
        #print("Grabbing camera %s" % self.camera_name, flush=True)
        return self.camera.grab()

    def retrieve(self):
        #print("Retrieving camera %s" % self.camera_name, flush=True)
        img = None
        ret = False
        if self.is_open():
            ret, img = self.camera.retrieve()
            #print("Updated img for %s" % self.camera_name, flush=True)
        else:
            print("Camera is closed %s" % self.camera_name, flush=True)
        self.lock.acquire()
        self.img = img
        self.lock.release()
        return ret

    def read(self):
        img = None
        ret = False
        if self.is_open():
            ret, img = self.camera.read()
        self.lock.acquire()
        self.img = img
        self.lock.release()
        return ret

    def get_img(self):
        self.lock.acquire()
        img = self.img
        self.lock.release()
        return img

    def get_png(self):
        self.lock.acquire()
        img = self.img
        self.lock.release()
        if img is not None:
            return cv2.imencode('.png', img)[1].tostring()
        return None

    def snapshot(self):
        img = None
        if self.is_open():
            r = requests.get(self.http_snapshot)
            img = Image.open(BytesIO(r.content))
        self.lock.acquire()
        self.img = img
        self.lock.release()

    def stop(self):
        print('Stopping camera: %s' % self.camera_name)
        self.do_run = False

    def run(self):
        print('Starting camera: %s' % self.camera_name, flush=True)

        while self.do_run:
            if not self.is_open():
                print('Camera is closed: %s' % self.camera_name)
                self.do_run = False
                continue

            try:
                self.grab()
                if self.retrieve() == False:
                    print('Failed to get image from camera: %s %s' % (self.camera_name, self.camera_url))
                    self.close()
                    continue
            except Exception as e:
                print('Camera grab exception: %s' % (e))
                self.close()
                continue

            #yield()
            time.sleep(1)

        print('Thread stopped camera: %s' % self.camera_name, flush=True)
