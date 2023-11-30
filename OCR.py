import os
from pathlib import Path
import sys
from datetime import datetime
import time
import threading
from threading import Thread

import cv2
import numpy
import pytesseract

import Linguist


def tesseract_location(root):

    try:
        pytesseract.pytesseract.tesseract_cmd = root
    except FileNotFoundError:
        print("Please double check the Tesseract file directory or ensure it's installed.")
        sys.exit(1)


class RateCounter:

    def __init__(self):
        self.start_time = None
        self.iterations = 0

    def start(self):
        """
        Starts a time.perf_counter() and sets it in the self.start_time attribute

        :return: self
        """
        self.start_time = time.perf_counter()
        return self

    def increment(self):
        """
        Increases the self.iterations attribute
        """
        self.iterations += 1

    def rate(self):
        """
        Returns the iterations/seconds
        """
        elapsed_time = (time.perf_counter() - self.start_time)
        return self.iterations / elapsed_time


class VideoStream:

    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False

    def start(self):
        """
        Creates a thread targeted at get(), which reads frames from CV2 VideoCapture

        :return: self
        """
        Thread(target=self.get, args=()).start()
        return self

    def get(self):
        """
        Continuously gets frames from CV2 VideoCapture and sets them as self.frame attribute
        """
        while not self.stopped:
            (self.grabbed, self.frame) = self.stream.read()

    def get_video_dimensions(self):
        """
        Gets the width and height of the video stream frames

        :return: height `int` and width `int` of VideoCapture
        """
        width = self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
        return int(width), int(height)

    def stop_process(self):
        """
        Sets the self.stopped attribute as True and kills the VideoCapture stream read
        """
        self.stopped = True


class OCR:

    # def __init__(self, exchange: VideoStream, language=None):
    def __init__(self):
        self.boxes = None
        self.stopped = False
        self.exchange = None
        self.language = None
        self.width = None
        self.height = None
        self.crop_width = None
        self.crop_height = None

    def start(self):
        """
        Creates a thread targeted at the ocr process
        :return: self
        """
        Thread(target=self.ocr, args=()).start()
        return self

    def set_exchange(self, video_stream):
        """
        Sets the self.exchange attribute with a reference to VideoStream class
        :param video_stream: VideoStream class
        """
        self.exchange = video_stream

    def set_language(self, language):
        """
        Sets the self.language parameter
        :param language: language code(s) for detecting custom languages in pytesseract
        """
        self.language = language

    def ocr(self):    
        while not self.stopped:
            if self.exchange is not None:  #Defends against an undefined VideoStream reference
                frame = self.exchange.frame

                #CUSTOM FRAME PRE-PROCESSING GOES HERE 
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

                frame = frame[self.crop_height:(self.height - self.crop_height),
                              self.crop_width:(self.width - self.crop_width)]

                self.boxes = pytesseract.image_to_data(frame, lang=self.language)

    def set_dimensions(self, width, height, crop_width, crop_height):
        """
        Sets the dimensions attributes

        :param width: Horizontal dimension of the VideoStream frame
        :param height: Vertical dimension of the VideoSteam frame
        :param crop_width: Horizontal crop amount if OCR is to be performed on a smaller area
        :param crop_height: Vertical crop amount if OCR is to be performed on a smaller area
        """
        self.width = width
        self.height = height
        self.crop_width = crop_width
        self.crop_height = crop_height

    def stop_process(self):
        """
        Sets the self.stopped attribute to True and kills the ocr() process
        """
        self.stopped = True


def capture_image(frame, captures=0):

    cwd_path = os.getcwd()
    Path(cwd_path + '/Images').mkdir(parents=False, exist_ok=True)

    now = datetime.now()
    name = "OCR " + now.strftime("%Y-%m-%d at %H-%M-%S-%f")[:-3] + '-' + str(captures + 1) + '.jpg'
    path = 'Images/' + name
    cv2.imwrite(path, frame)
    captures += 1
    print(name)
    return captures



def views(mode: int, confidence: int):

    conf_thresh = None
    color = None

    if mode == 1:
        conf_thresh = 75  # Only shows boxes with confidence greater than 75
        color = (0, 255, 0)  # Green

    if mode == 2:
        conf_thresh = 0  # Will show every box
        if confidence >= 50:
            color = (0, 255, 0)  # Green
        else:
            color = (0, 0, 255)  # Red

    if mode == 3:
        conf_thresh = 0  # Will show every box
        color = (int(float(confidence)) * 2.55, int(float(confidence)) * 2.55, 0)

    if mode == 4:
        conf_thresh = 0  # Will show every box
        color = (0, 0, 255)  # Red

    return conf_thresh, color


def put_ocr_boxes(boxes, frame, height, crop_width=0, crop_height=0, view_mode=1):

    if view_mode not in [1, 2, 3, 4]:
        raise Exception("A nonexistent view mode was selected. Only modes 1-4 are available")

    text = ''  # Initializing a string which will later be appended with the detected text
    if boxes is not None:  # Defends against empty data from tesseract image_to_data
        for i, box in enumerate(boxes.splitlines()):  # Next three lines turn data into a list
            box = box.split()
            if i != 0:
                if len(box) == 12:
                    x, y, w, h = int(box[6]), int(box[7]), int(box[8]), int(box[9])
                    conf = box[10]
                    word = box[11]
                    x += crop_width  # If tesseract was performed on a cropped image we need to 'convert' to full frame
                    y += crop_height

                    conf_thresh, color = views(view_mode, int(float(conf)))

                    if int(float(conf)) > conf_thresh:
                        cv2.rectangle(frame, (x, y), (w + x, h + y), color, thickness=1)
                        text = text + ' ' + word

        if text.isascii():  # CV2 is only able to display ascii chars at the moment
            cv2.putText(frame, text, (5, height - 5), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255))

    return frame, text


def put_crop_box(frame: numpy.ndarray, width: int, height: int, crop_width: int, crop_height: int):

    cv2.rectangle(frame, (crop_width, crop_height), (width - crop_width, height - crop_height),
                  (255, 0, 0), thickness=1)
    return frame


def put_rate(frame: numpy.ndarray, rate: float) -> numpy.ndarray:

    cv2.putText(frame, "{} Iterations/Second".format(int(rate)),
                (10, 35), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255))
    return frame


def put_language(frame: numpy.ndarray, language_string: str) -> numpy.ndarray:

    cv2.putText(frame, language_string,
                (10, 65), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255))
    return frame


def ocr_stream(crop: list[int, int], source: int = 0, view_mode: int = 1, language=None):

    captures = 0  # Number of still image captures during view session

    video_stream = VideoStream(source).start()  # Starts reading the video stream in dedicated thread
    img_wi, img_hi = video_stream.get_video_dimensions()

    if crop is None:  # Setting crop area and confirming valid parameters
        cropx, cropy = (200, 200)  # Default crop if none is specified
    else:
        cropx, cropy = crop[0], crop[1]
        if cropx > img_wi or cropy > img_hi or cropx < 0 or cropy < 0:
            cropx, cropy = 0, 0
            print("Impossible crop dimensions supplied. Dimensions reverted to 0 0")

    ocr = OCR().start()  # Starts optical character recognition in dedicated thread
    print("OCR stream started")
    print("Active threads: {}".format(threading.activeCount()))
    ocr.set_exchange(video_stream)
    ocr.set_language(language)
    ocr.set_dimensions(img_wi, img_hi, cropx, cropy)  # Tells the OCR class where to perform OCR (if img is cropped)

    cps1 = RateCounter().start()
    lang_name = Linguist.language_string(language)  # Creates readable language names from tesseract langauge code

    # Main display loop
    print("\nPUSH c TO CAPTURE AN IMAGE. PUSH q TO VIEW VIDEO STREAM\n")
    while True:

        # Quit condition:
        pressed_key = cv2.waitKey(1) & 0xFF
        if pressed_key == ord('q'):
            video_stream.stop_process()
            ocr.stop_process()
            print("OCR stream stopped\n")
            print("{} image(s) captured and saved to current directory".format(captures))
            break

        frame = video_stream.frame  # Grabs the most recent frame read by the VideoStream class

        # # # All display frame additions go here # # # CUSTOMIZABLE
        frame = put_rate(frame, cps1.rate())
        frame = put_language(frame, lang_name)
        frame = put_crop_box(frame, img_wi, img_hi, cropx, cropy)
        frame, text = put_ocr_boxes(ocr.boxes, frame, img_hi,
                                    crop_width=cropx, crop_height=cropy, view_mode=view_mode)
        # # # # # # # # # # # # # # # # # # # # # # # #

        # Photo capture:
        if pressed_key == ord('c'):
            print('\n' + text)
            captures = capture_image(frame, captures)

        cv2.imshow("realtime OCR", frame)
        cps1.increment()  # Incrementation for rate counter
