"""
    A Detector representation
"""
import edgetpu.detection.engine
import cv2
import time
from PIL import Image
from datetime import datetime


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
    
    def process_img(self, start_ms, threshold, img):
        detections = []
        input = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # convert to RGB color space
        img_pil = Image.fromarray(input)
        results = self.engine.detect_with_image(img_pil, threshold, keep_aspect_ratio=True, relative_coord=False, top_k=5)
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
