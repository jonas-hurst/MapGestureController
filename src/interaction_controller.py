import math

from cameracontrol import *
from screen import *
import geom
from websocketserver import Server
from constants import *
import touchcontrol as tc


class CameraException(Exception):
    pass


class InteractionController:
    def __init__(self, guicontext, infodata):

        self.guicontext = guicontext

        self.infodata = infodata

        self.screens = SCREEN_SINGLE_ABOVE

        self.screen_total_height = max([screen.px_height for screen in self.screens])
        self.screen_total_width = sum([screen.px_width for screen in self.screens])

        self.interaction_mechanism: InteractionMechanism = InteractionMechanism.SELECT_BOTH_PAN_BOTH
        self.pointing_mechanism: PointingMechanism = PointingMechanism.POINTER_TO_OBJECT

        self.touch_control_enabled = False
        self.show_camerafeed_enabled = False

        self.__tracker_controller = TrackerController(visualize=self.show_camerafeed_enabled)

        self.current_operation: Operation = Operation.IDLE  # Operation performed in the current frame
        self.previous_operation: Operation = Operation.IDLE  # Operation performed in the alst frame

        self.last_tap: float = 0  # indicates time when last tap happened

        self.prev_lefthand_pointing = (-1, -1)
        self.left_hand_coords_history: list[Point3D] = []
        self.prev_righthand_pointing = (1, -1)
        self.right_hand_coords_history: list[Point3D] = []

        self.reference_screenpos_for_rel_pointing: Union[None, tuple[int, int]] = None
        self.reference_handpos_for_rel_pointing: Union[None, Point3D] = None

    def start_camera(self):
        camera_numbers = self.__tracker_controller.get_camera_count()
        if camera_numbers < 1:
            raise CameraException("No camera detected")
        if camera_numbers > 1:
            raise CameraException("Multiple cameras not supported")

        camera_thread = threading.Thread(target=self.cameraloop, daemon=True)
        self.__tracker_controller.initialize_tracking()
        camera_thread.start()

    def stop_camera(self):
        if self.__tracker_controller.camera_running:
            self.__tracker_controller.camera_running = False
            self.__tracker_controller.stopDevice()

    def toggle_show_camerafeed(self, visualize: bool):
        self.show_camerafeed_enabled = visualize
        self.__tracker_controller.visualize = visualize

    def set_screen_environment(self, screens: tuple[Screen, ...]):
        self.screens = screens
        self.screen_total_width = sum([screen.px_width for screen in self.screens])

    def get_1euro_min_cutoff(self):
        return self.__tracker_controller.minCutoff

    def get_1euro_beta_value(self):
        return self.__tracker_controller.beta

    def get_1euro_tune_function(self):
        return self.__tracker_controller.tune_filters

    def cameraloop(self):
        server = Server()
        server.open_server()

        message = {
            "centercross": True if self.pointing_mechanism == PointingMechanism.OBJECT_TO_POITNER else False,
            "right": {
                "present": False,
                "fine": False,
                "position": {
                    "x": 0,
                    "y": 0
                }
            },
            "left": {
                "present": False,
                "fine": False,
                "position": {
                    "x": 0,
                    "y": 0
                }
            }
        }

        while True:
            message["centercross"] = True if self.pointing_mechanism == PointingMechanism.OBJECT_TO_POITNER else False

            bodyresult: BodyResult = self.__tracker_controller.getBodyCaptureData()

            if self.show_camerafeed_enabled:
                self.guicontext.set_bitmap(self.__tracker_controller.color_image_rgb)

            self.infodata["fps"] = self.__tracker_controller.fps
            self.infodata["bodies"] = self.__tracker_controller.number_tracked_bodies
            self.infodata["pitch"] = round(self.__tracker_controller.pitch * (180 / math.pi), 1)
            self.infodata["roll"] = round(self.__tracker_controller.roll * (180 / math.pi), 1)

            # Add Left Hand state to history
            if len(self.left_hand_coords_history) > 3:
                self.left_hand_coords_history.pop(0)
            try:
                self.left_hand_coords_history.append(bodyresult.left_hand_tip)
            except AttributeError:
                self.left_hand_coords_history.append(Point3D(0, 0, 0))

            # Add Right hand state to history
            if len(self.right_hand_coords_history) > 3:
                self.right_hand_coords_history.pop(0)
            try:
                self.right_hand_coords_history.append(bodyresult.right_hand_tip)
            except AttributeError:
                self.right_hand_coords_history.append(Point3D(0, 0, 0))

            if bodyresult is not None:
                self.process_bodyresult(bodyresult, message)
            else:
                message["right"]["present"] = False
                message["left"]["present"] = False
                tc.finger_up()

            self.infodata["operation"] = self.current_operation.name

            server.send_json(message)
            self.guicontext.set_datagrid_values(self.infodata)

            if not self.__tracker_controller.camera_running:
                break

        server.close_server()

    def process_bodyresult(self, bodyresult, message):
        self.infodata["left"] = bodyresult.left_hand_state.name
        self.infodata["right"] = bodyresult.right_hand_state.name
        self.infodata["cut"] = self.__tracker_controller.minCutoff
        self.infodata["beta"] = self.__tracker_controller.beta

        right_handresult, left_handresult = self.process_hands(bodyresult, message)
        right_hand_pointing_to_screen, coords_r, intersect_point_r = right_handresult
        screen_x_r, screen_y_r = coords_r
        left_hand_pointing_to_screen, coords_l, intersect_point_l = left_handresult
        screen_x_l, screen_y_l = coords_l

        # Check if at least one hand is pointing to the screen.
        # If not, exit this method
        if not right_hand_pointing_to_screen and not left_hand_pointing_to_screen:
            self.previous_operation = self.current_operation
            self.current_operation = Operation.IDLE
            return

        # After here only if if hand points to screen is on screen
        self.previous_operation = self.current_operation
        self.current_operation = self.detect_operation_handstate(
            bodyresult,
            left_hand_pointing_to_screen,
            right_hand_pointing_to_screen,
            intersect_point_l,
            intersect_point_r)

        operation_transition: OperationTransition = self.get_operation_transition()

        if self.touch_control_enabled:

            if self.current_operation == Operation.SELECT_RIGHTHAND:
                screen_x_r, screen_y_r = self.prev_righthand_pointing
            if self.current_operation == Operation.SELECT_LEFTHAND:
                screen_x_l, screen_y_l = self.prev_lefthand_pointing

            self.process_transition(operation_transition, screen_x_l, screen_y_l, screen_x_r, screen_y_r)
            self.process_operation(screen_x_l, screen_y_l, screen_x_r, screen_y_r)

        self.prev_righthand_pointing = (screen_x_r, screen_y_r)
        self.prev_lefthand_pointing = (screen_x_l, screen_y_l)

    def process_hands(self, bodyresult: BodyResult, message: dict) -> tuple[tuple[bool, tuple[int, int], Point3D], tuple[bool, tuple[int, int], Point3D]]:

        hand_pointing_to_screen_r, coords_r, intersect_point_r = self.process_hand(Handednes.RIGHT, bodyresult, message)
        hand_pointing_to_screen_l, coords_l, intersect_point_l = self.process_hand(Handednes.LEFT, bodyresult, message)

        if hand_pointing_to_screen_r and not hand_pointing_to_screen_l and bodyresult.left_hand.y < bodyresult.left_elbow.y:
            coords_r = self.handle_fine_pointing(bodyresult.right_hand, coords_r, message, "right")
        elif hand_pointing_to_screen_r:
            self.reference_screenpos_for_rel_pointing = None
            self.reference_handpos_for_rel_pointing = None
            coords_r = self.handle_coarse_pointing(coords_r, self.prev_righthand_pointing, message, "right")

        if hand_pointing_to_screen_l and not hand_pointing_to_screen_r and bodyresult.right_hand.y < bodyresult.right_elbow.y:
            coords_l = self.handle_fine_pointing(bodyresult.left_hand, coords_l, message, "left")
        elif hand_pointing_to_screen_l:
            self.reference_screenpos_for_rel_pointing = None
            self.reference_handpos_for_rel_pointing = None
            coords_l = self.handle_coarse_pointing(coords_l, self.prev_lefthand_pointing, message, "left")

        result_righthand = (hand_pointing_to_screen_r, coords_r, intersect_point_r)
        result_lefthand = (hand_pointing_to_screen_l, coords_l, intersect_point_l)

        return result_righthand, result_lefthand

    def process_hand(self, hand: Handednes, bodyresult: BodyResult, message: dict) -> tuple[bool, tuple[int, int], Point3D]:
        if hand == Handednes.INVALID:
            raise ValueError("hand value is INVALID. Must bei either LEFT or RIGHT")

        pointer = bodyresult.right_pointer if hand == Handednes.RIGHT else bodyresult.left_pointer
        msg_hand = "right" if hand == Handednes.RIGHT else "left"

        screen_x, screen_y, intersect_point = self.get_screen_intersection(pointer)

        hand_pointing_to_screen = True
        if screen_x == -1 and screen_y == -1:
            hand_pointing_to_screen = False
            message[msg_hand]["present"] = False

        coords = (screen_x, screen_y)

        return hand_pointing_to_screen, coords, intersect_point

    def get_screen_intersection(self, pointer: geom.Line) -> tuple[int, int, Point3D]:
        # Calculate the point in 3D-space wehre pointer-line and infinite screen-plain intersect
        # A check whether this point is on screen occurs later
        screen_id = -1
        screen_x, screen_y = -1, -1
        intersect_point = Point3D(-1, -1, -1)
        for screen in self.screens:
            try:
                intersect_point = screen.screen_plain.intersect_line(pointer)
            except geom.ParallelError:
                continue

            # If line-plain intersection point is on screen, try-block is executed
            # If it is not, except block executes.
            try:
                screen_x, screen_y = screen.coords_to_px(intersect_point)
                screen_id = screen.screen_id
            except ValueError:
                continue

        # TODO: Properly calculate pixel position, do not hard-code them like done below

        # No intersection with any screen
        if screen_id == -1:
            return -1, -1, intersect_point

        if screen_id == 0:
            return 2 * 1920 + screen_x, screen_y, intersect_point

        if screen_id == 1:
            return 1920 + screen_x, screen_y, intersect_point

        if screen_id == 2:
            return 1920 - screen_x, screen_y, intersect_point

        if screen_id == 3:
            return screen_x, screen_y, intersect_point

        return -1, -1, intersect_point

    def handle_fine_pointing(self, current_handposition: Point3D, coords, message: dict, msg_hand: str) -> tuple[int, int]:

        # TODO: ALso handle fine pointing when ray does no longer intersect screen?

        screen_x, screen_y = coords

        if self.reference_handpos_for_rel_pointing is None:
            self.reference_handpos_for_rel_pointing = current_handposition
        if self.reference_screenpos_for_rel_pointing is None:
            self.reference_screenpos_for_rel_pointing = (screen_x, screen_y)

        screen_x = self.reference_screenpos_for_rel_pointing[0] + int(0.2 * (screen_x - self.reference_screenpos_for_rel_pointing[0]))
        screen_y = self.reference_screenpos_for_rel_pointing[1] + int(0.2 * (screen_y - self.reference_screenpos_for_rel_pointing[1]))

        message[msg_hand]["present"] = True
        message[msg_hand]["fine"] = True
        message[msg_hand]["position"]["x"] = screen_x
        message[msg_hand]["position"]["y"] = screen_y

        return screen_x, screen_y

    def handle_coarse_pointing(self, coords: tuple[int, int], prev_coords: tuple[int, int], message: dict, msg_hand: str) -> tuple[int, int]:

        screen_x, screen_y = coords
        prev_screen_x, prev_screen_y = prev_coords

        # prevent point jitter: if px-offset is <6 px compared to prev. frame, then use old values
        if abs(screen_x - prev_screen_x) < 5:
            screen_x = prev_screen_x
        if abs(screen_y - prev_screen_y) < 5:
            screen_y = prev_screen_y

        message[msg_hand]["present"] = True
        message[msg_hand]["fine"] = False
        message[msg_hand]["position"]["x"] = screen_x
        message[msg_hand]["position"]["y"] = screen_y

        coords = (screen_x, screen_y)

        return coords

    def detect_operation_handstate(self, bodyresult: BodyResult, left_pointing: bool, right_pointing: bool, intersect_point_l: Point3D, intersect_point_r: Point3D) -> Operation:
        if left_pointing and right_pointing and bodyresult.right_hand_state == HandState.CLOSED and bodyresult.left_hand_state == HandState.CLOSED:
            return Operation.ZOOM

        if self.interaction_mechanism == InteractionMechanism.SELECT_RIGHT_PAN_LEFT or self.interaction_mechanism == InteractionMechanism.SELECT_BOTH_PAN_BOTH:
            if right_pointing and self.detect_righthand_selection(bodyresult, intersect_point_r):
                return Operation.SELECT_RIGHTHAND
            if bodyresult.left_hand_state == HandState.CLOSED and left_pointing:
                return Operation.PAN_LEFTHAND

        if self.interaction_mechanism == InteractionMechanism.SELECT_LEFT_PAN_RIGHT or self.interaction_mechanism == InteractionMechanism.SELECT_BOTH_PAN_BOTH:
            if left_pointing and self.detect_lefthand_selection(bodyresult, intersect_point_l):
                return Operation.SELECT_LEFTHAND
            if bodyresult.right_hand_state == HandState.CLOSED and right_pointing:
                return Operation.PAN_RIGHTHAND

        return Operation.IDLE

    def detect_righthand_selection(self, bodyresult: BodyResult, intersection_point_r: Point3D) -> bool:

        if bodyresult.right_hand_state == HandState.CLOSED or bodyresult.left_hand_state == HandState.CLOSED:
            return False

        # Check if each hand point is closer to camera than the one before
        intersection_point_r_plaine = Point3D(intersection_point_r.x, 0, intersection_point_r.z)
        for idx in range(len(self.right_hand_coords_history) - 1):
            current_plaine = Point3D(self.right_hand_coords_history[idx].x, 0, self.right_hand_coords_history[idx].z)
            next_plaine = Point3D(self.right_hand_coords_history[idx+1].x, 0, self.right_hand_coords_history[idx+1].z)
            if current_plaine.distance(intersection_point_r_plaine) <= next_plaine.distance(intersection_point_r_plaine):
                return False

        oldest = self.right_hand_coords_history[0]
        latest = self.right_hand_coords_history[-1]

        if abs(oldest.y - latest.y) > 30:
            return False

        # Last hand position must be closer to camera than the onx x frames ago.
        # Msut exceed threshold
        if Point3D(latest.x, 0, latest.z).distance(Point3D(oldest.x, 0, oldest.z)) < 40:
            return False

        self.right_hand_coords_history.pop()
        self.right_hand_coords_history.append(Point3D(0, 0, 0))
        return True

    def detect_lefthand_selection(self, bodyresult: BodyResult, intersection_point_l: Point3D) -> bool:

        if bodyresult.left_hand_state == HandState.CLOSED or bodyresult.right_hand_state == HandState.CLOSED:
            return False

        intersection_point_l_plaine = Point3D(intersection_point_l.x, 0, intersection_point_l.z)
        for idx in range(len(self.left_hand_coords_history) - 1):
            current_plaine = Point3D(self.left_hand_coords_history[idx].x, 0, self.left_hand_coords_history[idx].z)
            next_plaine = Point3D(self.left_hand_coords_history[idx+1].x, 0, self.left_hand_coords_history[idx+1].z)
            if current_plaine.distance(intersection_point_l_plaine) <= next_plaine.distance(intersection_point_l_plaine):
                return False

        oldest = self.left_hand_coords_history[0]
        latest = self.left_hand_coords_history[-1]

        if abs(oldest.y - latest.y) > 30:
            return False

        if Point3D(latest.x, 0, latest.z).distance(Point3D(oldest.x, 0, oldest.z)) < 40:
            return False

        self.left_hand_coords_history.pop()
        self.left_hand_coords_history.append(Point3D(0, 0, 0))
        return True

    def get_operation_transition(self) -> OperationTransition:
        """
        Method to determine the appropriate transition between operations
        :return: Transition between operations
        """
        if self.previous_operation == self.current_operation:
            return OperationTransition.REMAINS

        if self.previous_operation == Operation.SELECT_LEFTHAND:
            if self.current_operation == Operation.SELECT_RIGHTHAND:
                return OperationTransition.SELECTLEFT_TO_SELECTRIGHT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.SELECTLEFT_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.SELECTLEFT_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.SELECTLEFT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.SELECTLEFT_TO_IDLE

        if self.previous_operation == Operation.SELECT_RIGHTHAND:
            if self.current_operation == Operation.SELECT_LEFTHAND:
                return OperationTransition.SELECTRIGHT_TO_SELECTLEFT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.SELECTRIGHT_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.SELECTRIGHT_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.SELECTRIGHT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.SELECTRIGHT_TO_IDLE

        if self.previous_operation == Operation.PAN_LEFTHAND:
            if self.current_operation == Operation.SELECT_LEFTHAND:
                return OperationTransition.PANLEFT_TO_SELECTLEFT
            if self.current_operation == Operation.SELECT_RIGHTHAND:
                return OperationTransition.PANLEFT_TO_SELECTRIGHT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.PANLEFT_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.PANLEFT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.PANLEFT_TO_IDLE

        if self.previous_operation == Operation.PAN_RIGHTHAND:
            if self.current_operation == Operation.SELECT_LEFTHAND:
                return OperationTransition.PANRIGHT_TO_SELECTLEFT
            if self.current_operation == Operation.SELECT_RIGHTHAND:
                return OperationTransition.PANRIGHT_TO_SELECTRIGHT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.PANRIGHT_TO_PANLEFT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.PANRIGHT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.PANRIGHT_TO_IDLE

        if self.previous_operation == Operation.ZOOM:
            if self.current_operation == Operation.SELECT_LEFTHAND:
                return OperationTransition.ZOOM_TO_SELECTLEFT
            if self.current_operation == Operation.SELECT_RIGHTHAND:
                return OperationTransition.ZOOM_TO_SELECTRIGHT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.ZOOM_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.ZOOM_TO_PANRIGHT
            if self.current_operation == Operation.IDLE:
                return OperationTransition.ZOOM_TO_IDLE

        if self.previous_operation == Operation.IDLE:
            if self.current_operation == Operation.SELECT_LEFTHAND:
                return OperationTransition.IDLE_TO_SELECTLEFT
            if self.previous_operation == Operation.SELECT_RIGHTHAND:
                return OperationTransition.IDLE_TO_SELECTRIGHT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.IDLE_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.IDLE_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.IDLE_TO_ZOOM

    def process_transition(self, transition: OperationTransition, x_left: int, y_left: int, x_right: int, y_right: int):
        if transition == OperationTransition.REMAINS:
            return
        if transition == OperationTransition.SELECTLEFT_TO_SELECTRIGHT:
            self.transition_from_selectleft()
            self.transition_to_selectright()
            return
        if transition == OperationTransition.SELECTLEFT_TO_PANLEFT:
            return
        if transition == OperationTransition.SELECTLEFT_TO_PANRIGHT:
            return
        if transition == OperationTransition.SELECTLEFT_TO_ZOOM:
            return
        if transition == OperationTransition.SELECTLEFT_TO_IDLE:
            return
        if transition == OperationTransition.SELECTRIGHT_TO_SELECTLEFT:
            self.transition_from_selectright()
            return
        if transition == OperationTransition.SELECTRIGHT_TO_PANLEFT:
            self.transition_from_selectright()
            self.transition_to_panleft(x_left, y_left)
            return
        if transition == OperationTransition.SELECTRIGHT_TO_PANRIGHT:
            self.transition_from_selectright()
            self.transition_to_panrigth(x_right, y_right)
            return
        if transition == OperationTransition.SELECTRIGHT_TO_ZOOM:
            self.transition_from_selectright()
            self.transition_to_zoom(x_left, y_left, x_right, y_right)
            return
        if transition == OperationTransition.SELECTRIGHT_TO_IDLE:
            self.transition_from_selectright()
            return
        if transition == OperationTransition.PANLEFT_TO_SELECTLEFT:
            self.transition_from_panleft()
            self.transition_to_selectleft()
            return
        if transition == OperationTransition.PANLEFT_TO_SELECTRIGHT:
            self.transition_from_panleft()
            self.transition_to_selectright()
            return
        if transition == OperationTransition.PANLEFT_TO_PANRIGHT:
            self.transition_from_panleft()
            self.transition_to_panrigth(x_right, y_right)
            return
        if transition == OperationTransition.PANLEFT_TO_ZOOM:
            self.transition_from_panleft()
            self.transition_to_zoom(x_left, y_left, x_right, y_right)
            return
        if transition == OperationTransition.PANLEFT_TO_IDLE:
            self.transition_from_panleft()
            return
        if transition == OperationTransition.PANRIGHT_TO_SELECTLEFT:
            self.transition_from_panright()
            self.transition_to_selectleft()
            return
        if transition == OperationTransition.PANRIGHT_TO_SELECTRIGHT:
            self.transition_from_panright()
            self.transition_to_selectright()
            return
        if transition == OperationTransition.PANRIGHT_TO_PANLEFT:
            self.transition_from_panright()
            return
        if transition == OperationTransition.PANRIGHT_TO_ZOOM:
            self.transition_from_panright()
            self.transition_to_zoom(x_left, y_left, x_right, y_right)
            return
        if transition == OperationTransition.PANRIGHT_TO_IDLE:
            self.transition_from_panright()
            return
        if transition == OperationTransition.ZOOM_TO_SELECTLEFT:
            self.transition_from_zoom()
            self.transition_to_selectleft()
            return
        if transition == OperationTransition.ZOOM_TO_SELECTRIGHT:
            self.transition_from_zoom()
            self.transition_to_selectright()
            return
        if transition == OperationTransition.ZOOM_TO_PANLEFT:
            self.transition_from_zoom()
            self.transition_to_panleft(x_left, y_left)
            return
        if transition == OperationTransition.ZOOM_TO_PANRIGHT:
            self.transition_from_zoom()
            self.transition_to_panrigth(x_right, y_right)
            return
        if transition == OperationTransition.ZOOM_TO_IDLE:
            self.transition_from_zoom()
            return
        if transition == OperationTransition.IDLE_TO_SELECTLEFT:
            self.transition_to_selectleft()
            return
        if transition == OperationTransition.IDLE_TO_SELECTRIGHT:
            self.transition_to_selectright()
            return
        if transition == OperationTransition.IDLE_TO_PANLEFT:
            self.transition_to_panleft(x_left, y_left)
            return
        if transition == OperationTransition.IDLE_TO_PANRIGHT:
            self.transition_to_panrigth(x_right, y_right)
            return
        if transition == OperationTransition.IDLE_TO_ZOOM:
            self.transition_to_zoom(x_left, y_left, x_right, y_right)
            return

    def transition_to_selectleft(self):
        pass

    def transition_from_selectleft(self):
        pass

    def transition_to_selectright(self):
        pass

    def transition_from_selectright(self):
        pass

    def transition_to_panleft(self, x_left: int, y_left: int):
        tc.finger_down((self.screen_total_width - x_left, y_left))

    def transition_from_panleft(self):
        tc.finger_up()

    def transition_to_panrigth(self, x_right: int, y_right: int):
        tc.finger_down((self.screen_total_width - x_right, y_right))

    def transition_from_panright(self):
        tc.finger_up()

    def transition_from_zoom(self):
        tc.two_fingers_up()

    def transition_to_zoom(self, x_left, y_left, x_right, y_right):
        tc.two_fingers_down((self.screen_total_width - x_left, y_left), (self.screen_total_width - x_right, y_right))

    def process_operation(self, x_left: int, y_left: int, x_right: int, y_right: int):
        if self.current_operation == Operation.SELECT_LEFTHAND:
            self.select_lefthand(x_left, y_left)

        if self.current_operation == Operation.SELECT_RIGHTHAND:
            self.select_righthand(x_right, y_right)

        if self.current_operation == Operation.PAN_RIGHTHAND:
            self.pan_righthand(x_right, y_right)

        if self.current_operation == Operation.PAN_LEFTHAND:
            self.pan_lefthand(x_left, y_left)

        if self.current_operation == Operation.ZOOM:
            self.zoom(x_left, y_left, x_right, y_right)

    def select_lefthand(self, x: int, y: int):
        t_current = time()
        if t_current - self.last_tap < 1.5:
            return

        if self.pointing_mechanism == PointingMechanism.POINTER_TO_OBJECT:
            x_prev, y_prev = self.prev_lefthand_pointing
            tc.tap((self.screen_total_width - x_prev, y_prev))

        if self.pointing_mechanism == PointingMechanism.OBJECT_TO_POITNER:
            tc.tap((int(self.screen_total_width / 2), int(self.screen_total_height/2)))

        self.last_tap = time()

    def select_righthand(self, x: int, y: int):
        t_current = time()
        if t_current - self.last_tap < 1.5:
            return

        if self.pointing_mechanism == PointingMechanism.POINTER_TO_OBJECT:
            x_prev, y_prev = self.prev_righthand_pointing
            tc.tap((self.screen_total_width - x_prev, y_prev))

        if self.pointing_mechanism == PointingMechanism.OBJECT_TO_POITNER:
            tc.tap((int(self.screen_total_width / 2), int(self.screen_total_height/2)))

        self.last_tap = time()

    def pan_righthand(self, x: int, y: int):
        tc.move_finger((self.prev_righthand_pointing[0]-x, y - self.prev_righthand_pointing[1]))
        self.prev_righthand_pointing = (x, y)

    def pan_lefthand(self, x: int, y: int):
        tc.move_finger((self.prev_lefthand_pointing[0]-x, y-self.prev_lefthand_pointing[1]))
        self.prev_lefthand_pointing = (x, y)

    def zoom(self, x_left, y_left, x_right, y_right):
        if self.prev_lefthand_pointing is None:
            self.prev_lefthand_pointing = (self.screen_total_width - x_left, y_left)
        if self.prev_righthand_pointing is None:
            self.prev_righthand_pointing = (self.screen_total_width - x_right, y_right)
        tc.move_two_fingers((self.prev_lefthand_pointing[0]-x_left, y_left-self.prev_lefthand_pointing[1]),
                            (self.prev_righthand_pointing[0]-x_right, y_right - self.prev_righthand_pointing[1]))
        self.prev_lefthand_pointing = (x_left, y_left)
        self.prev_righthand_pointing = (x_right, y_right)