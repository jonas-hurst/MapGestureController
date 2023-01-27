import pykinect_azure as pykinect
import mediapipe as mp
import numpy as np
from utils import CvFpsCalc
from model import *
import threading
from typing import Union
import geom


class BodyResult:
    def __init__(self, body: pykinect.Body, left_hand_state: str, right_hand_state: str):
        self.body_center = 0

        self.left_hand_state: str = left_hand_state
        self.left_hand: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_HAND_LEFT].position.x,
                                                    body.joints[pykinect.K4ABT_JOINT_HAND_LEFT].position.y,
                                                    body.joints[pykinect.K4ABT_JOINT_HAND_LEFT].position.z)
        self.left_elbow: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_ELBOW_LEFT].position.x,
                                                     body.joints[pykinect.K4ABT_JOINT_ELBOW_LEFT].position.y,
                                                     body.joints[pykinect.K4ABT_JOINT_ELBOW_LEFT].position.z)
        self.left_pointer: geom.Line = geom.Line.from_points(self.left_elbow, self.left_hand)

        self.right_hand_state = right_hand_state
        self.right_hand: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_HAND_RIGHT].position.x,
                                                     body.joints[pykinect.K4ABT_JOINT_HAND_RIGHT].position.y,
                                                     body.joints[pykinect.K4ABT_JOINT_HAND_RIGHT].position.z)
        self.right_elbow: geom.Point3D = geom.Point3D(body.joints[pykinect.K4ABT_JOINT_ELBOW_RIGHT].position.x,
                                                      body.joints[pykinect.K4ABT_JOINT_ELBOW_RIGHT].position.y,
                                                      body.joints[pykinect.K4ABT_JOINT_ELBOW_RIGHT].position.z)
        self.right_pointer: geom.Line = geom.Line.from_points(self.right_elbow, self.right_hand)


class TrackerController:
    def __init__(self, visualize=True):
        pykinect.initialize_libraries(track_body=True)

        self.camera_running = False
        self.fps: float = 0
        self.visualize: bool = visualize
        self.color_image_bgr: Union[np.ndarray, None] = None
        self.number_tracked_bodies = 0

        self.__device: Union[pykinect.Device, None] = None
        self.__tracker: Union[pykinect.Tracker, None] = None

        self.__body_frame = None

        self.__handProcessThread = threading.Thread()
        self.__mp_drawing = mp.solutions.drawing_utils
        self.__mp_drawing_styles = mp.solutions.drawing_styles
        self.__hands: Union[mp.solutions.hands.Hands, None] = None
        self.__handresult = None

        self.__keypoint_classifier: Union[KeyPointClassifier, None] = None
        self.__hand_sign_ids = []
        self.__brects = []
        self.__keypoint_classifier_labels = ["Opened", "Closed", "Pointer"]

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

    def captureFrame(self):
        self.fps = self.__cvFpsCalc.get()

        capture = self.__device.update()

        # Get the color image from the capture
        ret, color_image_bgr = capture.get_color_image()

        if not ret:
            return

        self.__body_frame = self.__tracker.update()

        self.number_tracked_bodies = self.__body_frame.get_num_bodies()

        if not self.__handProcessThread.is_alive():
            self.__handProcessThread = threading.Thread(target=self.process_hands, args=(color_image_bgr,))
            self.__handProcessThread.start()

        if self.visualize:
            self.visualizeImage(color_image_bgr)

    def visualizeImage(self, color_image):
        self.__body_frame.draw_bodies(color_image, pykinect.K4A_CALIBRATION_TYPE_COLOR)

        if self.__handresult is not None and self.__handresult.multi_hand_landmarks:
            for landmark, handedness, brect, hand_sign_id in \
                    zip(self.__handresult.multi_hand_landmarks, self.__handresult.multi_handedness, self.__brects, self.__hand_sign_ids):
                self.__mp_drawing.draw_landmarks(
                    color_image,
                    landmark,
                    mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style())
                self.draw_info_text(
                    color_image,
                    brect,
                    handedness,
                    self.__keypoint_classifier_labels[hand_sign_id],
                    "no finger gesture"
                    # point_history_classifier_labels[most_common_fg_id[0][0]],
                            )

        cv.putText(color_image, "FPS:" + str(self.fps), (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
        cv.putText(color_image, "FPS:" + str(self.fps), (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv.LINE_AA)

        self.color_image_bgr = color_image
        # cv.imshow("color image", color_image)

    def process_hands(self, color_image_bgr):
        color_image_rgb = cv.cvtColor(color_image_bgr, cv.COLOR_BGR2RGB)
        color_image_rgb.flags.writeable = False
        self.__handresult = self.__hands.process(color_image_rgb)

        self.__brects = []
        self.__hand_sign_ids = []
        if self.__handresult.multi_hand_landmarks:
            for landmark, handedness in zip(self.__handresult.multi_hand_landmarks, self.__handresult.multi_handedness):
                # calcualte bbox for hand
                self.__brects.append(calc_bounding_rect(color_image_bgr, landmark))
                # create landmark list
                landmark_list = calc_landmark_list(color_image_bgr, landmark)
                # pre-process landmark list
                pre_processed_landmark_list = pre_process_landmark(landmark_list)
                # classify hand state
                self.__hand_sign_ids.append(self.__keypoint_classifier(pre_processed_landmark_list))

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
