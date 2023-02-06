import math
import pykinect_azure as pykinect
import mediapipe as mp
import numpy as np
import cv2 as cv
from utils import CvFpsCalc, OneEuroFilter
from time import time
from model import *
import threading
from typing import Union
import geom
from constants import HandState, Handednes
from numbers import Real


class BodyResult:
    def __init__(self, body: pykinect.Body, left_hand_state: HandState, right_hand_state: HandState):
        self.body_center = 0

        self.nose: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_NOSE].position.x,
                                               body.joints[pykinect.K4ABT_JOINT_NOSE].position.y,
                                               body.joints[pykinect.K4ABT_JOINT_NOSE].position.z)

        self.left_hand_state: HandState = left_hand_state
        self.left_hand_tip: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_HANDTIP_LEFT].position.x,
                                                        body.joints[pykinect.K4ABT_JOINT_HANDTIP_LEFT].position.y,
                                                        body.joints[pykinect.K4ABT_JOINT_HANDTIP_LEFT].position.z)
        self.left_hand: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_HAND_LEFT].position.x,
                                                    body.joints[pykinect.K4ABT_JOINT_HAND_LEFT].position.y,
                                                    body.joints[pykinect.K4ABT_JOINT_HAND_LEFT].position.z)
        self.left_elbow: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_ELBOW_LEFT].position.x,
                                                     body.joints[pykinect.K4ABT_JOINT_ELBOW_LEFT].position.y,
                                                     body.joints[pykinect.K4ABT_JOINT_ELBOW_LEFT].position.z)
        self.left_pointer: geom.Line = geom.Line.from_points(self.nose, self.left_hand_tip)

        self.right_hand_state: HandState = right_hand_state
        self.right_hand_tip: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_HANDTIP_RIGHT].position.x,
                                                         body.joints[pykinect.K4ABT_JOINT_HANDTIP_RIGHT].position.y,
                                                         body.joints[pykinect.K4ABT_JOINT_HANDTIP_RIGHT].position.z)
        self.right_hand: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_HAND_RIGHT].position.x,
                                                     body.joints[pykinect.K4ABT_JOINT_HAND_RIGHT].position.y,
                                                     body.joints[pykinect.K4ABT_JOINT_HAND_RIGHT].position.z)
        self.right_elbow: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_ELBOW_RIGHT].position.x,
                                                      body.joints[pykinect.K4ABT_JOINT_ELBOW_RIGHT].position.y,
                                                      body.joints[pykinect.K4ABT_JOINT_ELBOW_RIGHT].position.z)
        self.right_pointer: geom.Line = geom.Line.from_points(self.nose, self.right_hand)


class Hand:
    def __init__(self, handednes: Handednes = Handednes.INVALID, handstate: HandState = HandState.UNTRACKED, bbox=None):
        self.handednes: Handednes = handednes
        self.handstate: HandState = handstate
        self.bbox = bbox


class TrackerController:
    """
    Class to perform Processing of Azure Kinect Imagery
    """
    def __init__(self, visualize=True):
        pykinect.initialize_libraries(track_body=True)

        self.camera_running = False
        self.fps: float = 0
        self.visualize: bool = visualize
        self.color_image_bgr: Union[np.ndarray, None] = None
        self.number_tracked_bodies = 0

        # for 1Euro filter
        self.minCutoff = 1
        self.beta = 0

        self.__device: Union[pykinect.Device, None] = None
        self.__tracker: Union[pykinect.Tracker, None] = None

        # Initialize list of 1-Euro-filters: Three filters per joint, one for each coordinate
        self.__filters_initialized = False
        self.__one_euro_filters: list[list[OneEuroFilter]] = []
        for _ in range(pykinect.K4ABT_JOINT_COUNT):
            joint_filters: list[OneEuroFilter] = []
            for __ in range(3):
                one_eur_filter = OneEuroFilter(0, 0, min_cutoff=self.minCutoff, beta=self.beta)
                joint_filters.append(one_eur_filter)
            self.__one_euro_filters.append(joint_filters)

        self.__body_frame = None
        self.__leftHand: Hand = Hand(Handednes.LEFT)
        self.__rightHand: Hand = Hand(Handednes.RIGHT)

        self.__handProcessThread = threading.Thread()
        self.__mp_drawing = mp.solutions.drawing_utils
        self.__mp_drawing_styles = mp.solutions.drawing_styles
        self.__hands: Union[mp.solutions.hands.Hands, None] = None
        self.__handresult = None

        self.__keypoint_classifier: Union[KeyPointClassifier, None] = None

        self.__cvFpsCalc = CvFpsCalc(buffer_len=10)

    def initialize_tracking(self):
        self.__device = self.startCamera()
        self.__tracker = self.startTracker()
        self.__hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0)
        self.__keypoint_classifier = KeyPointClassifier()
        self.camera_running = True

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

    def stopDevice(self):
        self.__device.close()
        self.__device = None
        self.__hands.close()
        self.__keypoint_classifier = None

    def getBodyCaptureData(self):
        """
        Method to be performed each frame
        :return: Result of body tracking, derived from hand gesture and skeleton
        """
        self.fps = self.__cvFpsCalc.get()

        capture = self.__device.update()

        capture_time = time()

        # Get the color image from the capture
        ret, color_image_bgr = capture.get_color_image()

        if not ret:
            return

        self.__body_frame = self.__tracker.update()

        self.number_tracked_bodies = self.__body_frame.get_num_bodies()

        if not self.__handProcessThread.is_alive():
            self.__handProcessThread = threading.Thread(target=self.process_hands, args=(cv.flip(color_image_bgr, 1),))
            self.__handProcessThread.start()

        if self.visualize:
            self.visualizeImage(color_image_bgr)

        if self.__body_frame.get_num_bodies() > 0:

            # on first body detected: initialize filters
            if not self.__filters_initialized:
                self.initialize_filters(self.__body_frame.get_body(0), capture_time)
                self.__filters_initialized = True
                return None

            body: pykinect.Body = self.__body_frame.get_body(0)

            # Filter coordinates
            self.filter_body_coordinates(body, capture_time)

            # Rotate coordinates to correct for camera pitch
            self.correct_pitch(body)

            result = BodyResult(body, self.__leftHand.handstate, self.__rightHand.handstate)
            return result
        else:
            return None

    def initialize_filters(self, body: pykinect.Body, t0: float):
        for jointfilterset, joint in zip(self.__one_euro_filters, body.joints):
            jointfilterset[0].x_prev = joint.position.x
            jointfilterset[0].t_prev = t0

            jointfilterset[1].x_prev = joint.position.y
            jointfilterset[1].t_prev = t0

            jointfilterset[2].x_prev = joint.position.z
            jointfilterset[2].t_prev = t0

    def tune_filters(self, min_cutoff: float, beta: float):
        self.minCutoff = min_cutoff
        self.beta = beta

        for jointfilterset in self.__one_euro_filters:
            for coord_filter in jointfilterset:
                coord_filter.min_cutoff = min_cutoff
                coord_filter.beta = beta

    def filter_body_coordinates(self, body: pykinect.Body, t: float):
        for jointfilterset, joint in zip(self.__one_euro_filters, body.joints):
            joint.position.x = jointfilterset[0](t, joint.position.x)
            joint.position.y = jointfilterset[1](t, joint.position.y)
            joint.position.z = jointfilterset[2](t, joint.position.z)

    def correct_pitch(self, body: pykinect.Body):
        # depth camera is angled 6 degrees to  bottom
        pitch_angle_internal = 6

        # TODO: Calculate pitch angle from IMU accelerometer
        pitch_angle_imu = 0

        pitch_angle = pitch_angle_internal + pitch_angle_imu

        if abs(pitch_angle) > 85:
            raise ValueError("Cannot perform correction: Danger of Gimbal Lock")

        angle_rad = angle * (math.pi / 180)
        matrix = np.array([[math.cos(angle_rad), -math.sin(angle_rad)],
                           [math.sin(angle_rad),  math.cos(angle_rad)]])
        vector = np.zeros(2)

        for joint in body.joints:
            # As rotation occurs around x-axis, we can neglect x-value as it remains the same anyway
            vector[0] = joint.position.y
            vector[1] = joint.position.z

            transformed = matrix @ vector  # matrix-vector multiplication

            joint.position.y = transformed[0]
            joint.position.z = transformed[1]


    def visualizeImage(self, color_image):
        """
        Generaet a cv2 image that can be displayed
        :param color_image: The color image taken by the camera (BGR color format), as np.ndarray
        :return: nothing
        """
        self.__body_frame.draw_bodies(color_image, pykinect.K4A_CALIBRATION_TYPE_COLOR)

        color_image = cv.flip(color_image, 1)

        if self.__leftHand.handstate != HandState.UNTRACKED:
            self.draw_info_text(color_image, self.__leftHand)
        if self.__rightHand.handstate != HandState.UNTRACKED:
            self.draw_info_text(color_image, self.__rightHand)

        if self.__handresult is not None and self.__handresult.multi_hand_landmarks:
            for landmark in self.__handresult.multi_hand_landmarks:
                self.__mp_drawing.draw_landmarks(
                    color_image,
                    landmark,
                    mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style())

        self.color_image_bgr = color_image
        # cv.imshow("color image", color_image)

    def process_hands(self, color_image_bgr):
        """
        Method to process color image (BGR color format).
        Mediapipe detects hand and landmarks, different model classifys hand state based on landmarks.
        :param color_image_bgr: the image from camera
        :return: nothing
        """
        color_image_rgb = cv.cvtColor(color_image_bgr, cv.COLOR_BGR2RGB)
        color_image_rgb.flags.writeable = False
        self.__handresult = self.__hands.process(color_image_rgb)
        right_hand_detected = False
        left_hand_detected = False
        if self.__handresult.multi_hand_landmarks:
            for landmark, handedness in zip(self.__handresult.multi_hand_landmarks, self.__handresult.multi_handedness):

                hand = Hand()
                if handedness.classification[0].label == "Left":
                    left_hand_detected = True
                    hand = self.__leftHand

                if handedness.classification[0].label == "Right":
                    right_hand_detected = True
                    hand = self.__rightHand

                # calcualte bbox for hand
                hand.bbox = calc_bounding_rect(color_image_bgr, landmark)

                # create landmark list
                landmark_list = calc_landmark_list(color_image_bgr, landmark)
                # pre-process landmark list
                pre_processed_landmark_list = pre_process_landmark(landmark_list)
                # classify hand state
                class_result = self.__keypoint_classifier(pre_processed_landmark_list)
                hand.handstate = HandState.from_classification_result(class_result)

        if not left_hand_detected:
            self.__leftHand.handstate = HandState.UNTRACKED
        if not right_hand_detected:
            self.__rightHand.handstate = HandState.UNTRACKED

    def draw_info_text(self, image, hand: Hand):
        """
        Add info text to image for visualization.
        :param image: Color image
        :param hand: Hand Inforrmation
        :return: nothing
        """
        brect = hand.bbox

        info_text = hand.handednes.name
        if hand.handstate != HandState.UNTRACKED:
            info_text = info_text + ':' + hand.handstate.name
        cv.putText(image, info_text, (brect[0] + 5, brect[1] - 4),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)

        # if finger_gesture_text != "":
        #     cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
        #                cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
        #     cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
        #                cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
        #                cv.LINE_AA)
