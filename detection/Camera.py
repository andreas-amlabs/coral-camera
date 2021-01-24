"""
    A camera representation
"""
import requests
from io import BytesIO

import cv2


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
