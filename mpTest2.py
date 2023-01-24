import copy
import csv
import itertools
import cv2 as cv

import pykinect_azure as pykinect

import mediapipe as mp

import numpy as np

from utils import CvFpsCalc

from model import *

from time import time

import threading


class GestureController:
    def __init__(self, visualize=True):
        pykinect.initialize_libraries(track_body=True)

        self.device: pykinect.Device = self.startCamera()
        self.tracker: pykinect.Tracker = self.startTracker()

        self.body_frame = None

        self.handProcessThread = threading.Thread()
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.handresult = None

        self.keypoint_classifier = KeyPointClassifier()
        self.hand_sign_ids = []
        self.brects = []
        self.keypoint_classifier_labels = ["Opened", "Closed", "Pointer"]

        self.visualize: bool = visualize

        self.cvFpsCalc = CvFpsCalc(buffer_len=10)
        self.fps = 0

    def start_cameraloop(self):
        with mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0) as hands:
            while True:
                t0 = time()
                self.fps = self.cvFpsCalc.get()
                self.captureFrame(hands)
                if cv.waitKey(1) == ord("q"):
                    break
                t1 = time()
                print(t1 - t0)

    def startCamera(self):
        device_config = pykinect.default_configuration
        device_config.color_resolution = pykinect.K4A_COLOR_RESOLUTION_720P
        device_config.depth_mode = pykinect.K4A_DEPTH_MODE_WFOV_2X2BINNED
        device_config.camera_fps = pykinect.K4A_FRAMES_PER_SECOND_30
        device_config.synchronized_images_only = True

        device = pykinect.start_device(config=device_config)
        return device

    def startTracker(self):
        tracker_config = pykinect.default_tracker_configuration
        tracker_config.tracker_processing_mode = pykinect.K4ABT_TRACKER_PROCESSING_MODE_GPU
        tracker_config.gpu_device_id = 1

        bodytracker = pykinect.start_body_tracker(tracker_configuration=tracker_config)
        return bodytracker

    def captureFrame(self, hands):
        capture = self.device.update()

        # Get the color image from the capture
        ret, color_image = capture.get_color_image()

        if not ret:
            return

        self.body_frame = self.tracker.update()

        if not self.handProcessThread.is_alive():
            self.handProcessThread = threading.Thread(target=self.process_hands, args=(hands, color_image))
            self.handProcessThread.start()

        if self.visualize:
            self.visualizeImage(color_image)

    def visualizeImage(self, image):
        color_image = self.body_frame.draw_bodies(image, pykinect.K4A_CALIBRATION_TYPE_COLOR)

        if self.handresult is not None and self.handresult.multi_hand_landmarks:
            for landmark, handedness, brect, hand_sign_id in \
                    zip(self.handresult.multi_hand_landmarks, self.handresult.multi_handedness, self.brects, self.hand_sign_ids):
                self.mp_drawing.draw_landmarks(
                    color_image,
                    landmark,
                    mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style())
                self.draw_info_text(
                    color_image,
                    brect,
                    handedness,
                    self.keypoint_classifier_labels[hand_sign_id],
                    "no finger gesture"
                    # point_history_classifier_labels[most_common_fg_id[0][0]],
                            )

        cv.putText(image, "FPS:" + str(self.fps), (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
        cv.putText(image, "FPS:" + str(self.fps), (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv.LINE_AA)

        cv.imshow("color image", color_image)

    def process_hands(self, hands, imageBGR):
        color_image_rgb = cv.cvtColor(imageBGR, cv.COLOR_BGR2RGB)
        color_image_rgb.flags.writeable = False
        self.handresult = hands.process(color_image_rgb)

        self.brects = []
        self.hand_sign_ids = []
        if self.handresult.multi_hand_landmarks:
            for landmark, handedness in zip(self.handresult.multi_hand_landmarks, self.handresult.multi_handedness):
                # calcualte bbox for hand
                self.brects.append(calc_bounding_rect(imageBGR, landmark))
                # create landmark list
                landmark_list = calc_landmark_list(imageBGR, landmark)
                # pre-process landmark list
                pre_processed_landmark_list = pre_process_landmark(landmark_list)
                # classify hand state
                self.hand_sign_ids.append(self.keypoint_classifier(pre_processed_landmark_list))

    def draw_info_text(self, image, brect, handedness, hand_sign_text, finger_gesture_text):
        cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[1] - 22),
                     (0, 0, 0), -1)

        info_text = handedness.classification[0].label[0:]
        if hand_sign_text != "":
            info_text = info_text + ':' + hand_sign_text
        cv.putText(image, info_text, (brect[0] + 5, brect[1] - 4),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)

        if finger_gesture_text != "":
            cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
                       cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
            cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
                       cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
                       cv.LINE_AA)


def main():
    GestureController(visualize=True)


if __name__ == "__main__":
    main()