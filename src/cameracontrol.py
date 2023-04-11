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

        self.nose: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_NOSE].position.x,
                                               body.joints[pykinect.K4ABT_JOINT_NOSE].position.y,
                                               body.joints[pykinect.K4ABT_JOINT_NOSE].position.z)

        self.chest: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_SPINE_CHEST].position.x,
                                                body.joints[pykinect.K4ABT_JOINT_SPINE_CHEST].position.y,
                                                body.joints[pykinect.K4ABT_JOINT_SPINE_CHEST].position.z)

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
        self.left_shoulder: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_SHOULDER_LEFT].position.x,
                                                        body.joints[pykinect.K4ABT_JOINT_SHOULDER_LEFT].position.y,
                                                        body.joints[pykinect.K4ABT_JOINT_SHOULDER_LEFT].position.z)

        self.pointer_start_left = self.left_shoulder
        self.pointer_end_left = self.left_hand
        self.left_pointer: geom.Line = geom.Line.from_points(self.pointer_start_left, self.pointer_end_left)

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
        self.right_shoulder: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_SHOULDER_RIGHT].position.x,
                                                         body.joints[pykinect.K4ABT_JOINT_SHOULDER_RIGHT].position.y,
                                                         body.joints[pykinect.K4ABT_JOINT_SHOULDER_RIGHT].position.z)

        self.pointer_start_right = self.right_shoulder
        self.pointer_end_right = self.right_hand
        self.right_pointer: geom.Line = geom.Line.from_points(self.pointer_start_right, self.right_hand)


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
        self.color_image_rgb: Union[np.ndarray, None] = None
        self.number_tracked_bodies = 0

        # pitch and roll
        self.pitch = 0
        self.roll = 0

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
        self.__hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.2,
            min_tracking_confidence=0.3)
        self.__keypoint_classifier = KeyPointClassifier()
        self.camera_running = True

    def get_camera_count(self):
        return pykinect.Device.device_get_installed_count()

    def startCamera(self):
        device_config = pykinect.default_configuration
        device_config.color_resolution = pykinect.K4A_COLOR_RESOLUTION_1080P
        device_config.depth_mode = pykinect.K4A_DEPTH_MODE_NFOV_2X2BINNED
        device_config.camera_fps = pykinect.K4A_FRAMES_PER_SECOND_30
        device_config.color_format = pykinect.K4A_IMAGE_FORMAT_COLOR_BGRA32
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

        imu_sample = self.__device.update_imu()

        capture_time = time()

        # Get the color image from the capture
        ret, color_image_bgra = capture.get_color_image()

        if not ret:
            return

        color_image_rgb = cv.cvtColor(color_image_bgra, cv.COLOR_BGR2RGB)

        self.__body_frame = self.__tracker.update()

        self.calc_roll_pitch(imu_sample)

        self.number_tracked_bodies = self.__body_frame.get_num_bodies()

        if not self.__handProcessThread.is_alive():
            self.__handProcessThread = threading.Thread(target=self.process_hands, args=(cv.flip(color_image_rgb, 1),))
            self.__handProcessThread.start()

        if self.visualize:
            self.visualizeImage(color_image_rgb)

        # get number of detected bodies in frame
        num_bodies = self.__body_frame.get_num_bodies()

        # End procesing when no bodies are detected
        if num_bodies < 1:
            self.__filters_initialized = False
            return None

        # Identify the body closest to camera and use only it for further processing
        closest_body_idx = None
        closest_body_distance = float("inf")
        for body_idx in range(num_bodies):
            x = self.__body_frame.get_body(body_idx).joints[pykinect.K4ABT_JOINT_SPINE_CHEST].position.z
            y = self.__body_frame.get_body(body_idx).joints[pykinect.K4ABT_JOINT_SPINE_CHEST].position.y
            z = self.__body_frame.get_body(body_idx).joints[pykinect.K4ABT_JOINT_SPINE_CHEST].position.z
            sq_dist_camera = x*x - y*y - z*z
            if sq_dist_camera < closest_body_distance:
                closest_body_idx = body_idx
                closest_body_distance = sq_dist_camera

        body = self.__body_frame.get_body(closest_body_idx)

        # on first frame where body is detected: initialize filters
        if not self.__filters_initialized:
            self.initialize_filters(body, capture_time)
            self.__filters_initialized = True
            return None

        # Filter coordinates
        self.filter_body_coordinates(body, capture_time)

        # Rotate coordinates to correct for camera pitch
        self.correct_roll_pitch(body)

        result = BodyResult(body, self.__leftHand.handstate, self.__rightHand.handstate)
        return result

    def calc_roll_pitch(self, imu_sample: pykinect.ImuSample):
        """
        Calculate devices roll (rotation around device´s z-axis) and pitch (rotation around devices x-axis) angles
        from IMU gyroscope measures
        :param imu_sample: Sample of IMU measuremnts
        :return: None
        """

        acc_sample = imu_sample.acc
        acc_x = acc_sample[0]
        acc_y = acc_sample[1]
        acc_z = acc_sample[2]
        self.pitch = math.asin(acc_x / math.sqrt(sum(i ** 2 for i in acc_sample)))
        self.roll = math.atan(acc_y / acc_z)

    def initialize_filters(self, body: pykinect.Body, t0: float):
        """
        Method to initialize 1-Euro-filters for filtering joint coordinates
        :param body: Tracked body object whose joints should be filtered
        :param t0: Timestamp at which body was tracked in sesconds
        :return: None
        """

        for jointfilterset, joint in zip(self.__one_euro_filters, body.joints):
            jointfilterset[0].x_prev = joint.position.x
            jointfilterset[0].t_prev = t0

            jointfilterset[1].x_prev = joint.position.y
            jointfilterset[1].t_prev = t0

            jointfilterset[2].x_prev = joint.position.z
            jointfilterset[2].t_prev = t0

    def tune_filters(self, min_cutoff: float, beta: float):
        """
        Method to adjust 1-Euro-filter parameters
        :param min_cutoff: Minimum-Cutoff value
        :param beta: Beta value
        :return: None
        """

        self.minCutoff = min_cutoff
        self.beta = beta

        for jointfilterset in self.__one_euro_filters:
            for coord_filter in jointfilterset:
                coord_filter.min_cutoff = min_cutoff
                coord_filter.beta = beta

    def filter_body_coordinates(self, body: pykinect.Body, t: float):
        """
        Method to perform 1-Euro-filtering on Body joint coordinates
        :param body: Tracked body object whose joints should be filtered
        :param t: Timestamp at which body was tracked in seconds
        :return: None
        """

        for jointfilterset, joint in zip(self.__one_euro_filters, body.joints):
            joint.position.x = jointfilterset[0](t, joint.position.x)
            joint.position.y = jointfilterset[1](t, joint.position.y)
            joint.position.z = jointfilterset[2](t, joint.position.z)

    def correct_roll_pitch(self, body: pykinect.Body):
        """
        Method to correct for roll (rotation around device´s z-axis) and pitch (rotation around device´s x-axis)
        :param body: Body object, whose coordinates should be corrected
        :return: None
        """

        # depth camera is angled 6 degrees to  bottom
        pitch_angle_internal = -6 * (math.pi / 180)
        pitch_angle = pitch_angle_internal - self.pitch

        roll_angle = - self.roll

        if abs(pitch_angle) > math.pi / 2 or abs(roll_angle) > math.pi / 2:
            raise ValueError("Cannot perform correction: Danger of Gimbal Lock")

        # matrix to corect for pitch angle
        # mathmatically speaking: rotation around x axis
        matrix_pitch_correction = np.array([[1, 0, 0],
                                            [0, math.cos(pitch_angle), -math.sin(pitch_angle)],
                                            [0, math.sin(pitch_angle),  math.cos(pitch_angle)]])

        # matrix to correct for roll angle
        # mathmatically speaking, this is a rotation around z axis
        matrix_roll_correction = np.array([[math.cos(roll_angle), -math.sin(roll_angle), 0],
                                           [math.sin(roll_angle),  math.cos(roll_angle), 0],
                                           [0, 0, 1]])

        rotation_matrix = matrix_roll_correction @ matrix_pitch_correction

        vector = np.zeros(3)

        for joint in body.joints:
            # As rotation occurs around x-axis, we can neglect x-value as it remains the same anyway
            vector[0] = joint.position.x
            vector[1] = joint.position.y
            vector[2] = joint.position.z

            transformed = rotation_matrix @ vector  # matrix-vector multiplication

            joint.position.x = transformed[0]
            joint.position.y = transformed[1]
            joint.position.z = transformed[2]

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

        self.color_image_rgb = color_image
        # cv.imshow("color image", color_image)

    def process_hands(self, color_image_rgb):
        """
        Method to process color image (BGR color format).
        Mediapipe detects hand and landmarks, different model classifys hand state based on landmarks.
        :param color_image_bgr: the image from camera
        :return: nothing
        """
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
                hand.bbox = calc_bounding_rect(color_image_rgb, landmark)

                # create landmark list
                landmark_list = calc_landmark_list(color_image_rgb, landmark)
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
