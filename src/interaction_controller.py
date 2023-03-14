import math

from cameracontrol import *
from screen import *
import geom
from websocketserver import Server
from constants import *
import touchcontrol as tc

from collections import Counter
import typing

class CameraException(Exception):
    pass


class InteractionController:
    def __init__(self, guicontext, infodata):

        self.cameraloop_thread: Union[threading.Thread, None] = None

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
        self.left_hand_state_history: list[HandState] = []
        self.right_hand_state_history: list[HandState] = []

        # Properties needed for relative fine pointing mechanism
        self.right_hand_relative_pointing: bool = False
        self.left_hand_relative_pointing: bool = False
        self.reference_screen_point_for_rel_pointing: Union[None, Point3D] = None
        self.reference_screenpos_for_rel_pointing: Union[None, tuple[int, int]] = None
        self.reference_handpos_for_rel_pointing: Union[None, Point3D] = None
        self.reference_screen_for_rel_pointing: Union[None, Screen] = None

    def start_camera(self):
        """
        Initializes and starts the camera.
        After initialization, cameraloop starts executing in a new thread.
        :return: None
        """
        camera_numbers = self.__tracker_controller.get_camera_count()
        if camera_numbers < 1:
            raise CameraException("No camera detected")
        if camera_numbers > 1:
            raise CameraException("Multiple cameras not supported")

        self.cameraloop_thread = threading.Thread(target=self.cameraloop, daemon=True)
        self.__tracker_controller.initialize_tracking()
        self.cameraloop_thread.start()

    def stop_camera(self):
        """ Stops the thread in which camera feed is processed. """
        if self.__tracker_controller.camera_running:
            self.__tracker_controller.camera_running = False
            self.cameraloop_thread.join()  # wait for cameraloop thread to finnish its last iteratino
            self.__tracker_controller.stopDevice()

    def toggle_show_camerafeed(self, visualize: bool):
        """ Initiates the camerafeed showing on screen. """
        self.show_camerafeed_enabled = visualize
        self.__tracker_controller.visualize = visualize

    def set_screen_environment(self, screens: tuple[Screen, ...]):
        """ Sets a new screen environment. """
        self.screens = screens
        self.screen_total_height = max([screen.px_height for screen in self.screens])
        self.screen_total_width = sum([screen.px_width for screen in self.screens])

    def get_1euro_min_cutoff(self) -> float:
        """ Gets the current Minimum cutoff frequency value used in 1€ filters. """
        return self.__tracker_controller.minCutoff

    def get_1euro_beta_value(self) -> float:
        """ Gets the current beta value used in 1€ filters. """
        return self.__tracker_controller.beta

    def get_1euro_tune_function(self) -> typing.Callable[[float, float], None]:
        """ Gets the function that is used to tune 1€ filters. """
        return self.__tracker_controller.tune_filters

    def cameraloop(self):
        """ Captuers and processes camera feed. """

        # Start websocket server to communicate with Chrome extension
        server = Server()
        server.open_server()

        # Initialize message to be sent through websocket server
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

        # Loop to continuously captuer camera feed
        while True:

            # update websocket message to display cross in center in feature-to-pointer method
            message["centercross"] = True if self.pointing_mechanism == PointingMechanism.OBJECT_TO_POITNER else False

            # Get result of body tracking
            bodyresult: BodyResult = self.__tracker_controller.getBodyCaptureData()

            # Show camerafeed in GUI (if enabled)
            if self.show_camerafeed_enabled:
                self.guicontext.set_bitmap(self.__tracker_controller.color_image_rgb)

            # Update infodata dictionary (will show in grid in GUI)
            self.infodata["fps"] = self.__tracker_controller.fps
            self.infodata["bodies"] = self.__tracker_controller.number_tracked_bodies
            self.infodata["pitch"] = round(self.__tracker_controller.pitch * (180 / math.pi), 1)
            self.infodata["roll"] = round(self.__tracker_controller.roll * (180 / math.pi), 1)

            self.fill_histories(bodyresult)

            if bodyresult is not None:
                # Process results from body tracking
                self.process_bodyresult(bodyresult, message)
            else:
                message["right"]["present"] = False
                message["left"]["present"] = False
                tc.finger_up()

            # update infodata dict
            self.infodata["operation"] = self.current_operation.name

            server.send_json(message)  # send message through websocket
            self.guicontext.set_datagrid_values(self.infodata)  # update datagrid in gui with info data

            # break cameraloop
            if not self.__tracker_controller.camera_running:
                break

        # Close websocket server
        server.close_server()

    def fill_histories(self, bodyresult: BodyResult):
        """
        Method to manage lists of bodyresult values from past frames
        :param bodyresult: Result of Body Tracking
        :return: None
        """

        def add_item_to_history(history: list, item, list_max_length: int):
            """
            Adds an item to a history list
            :param history: The history list to be added to
            :param item: The item to be added to the history list
            :return:
            """
            if len(history) > list_max_length:
                history.pop(0)

            history.append(item)

        hand_coordinate_history_length = 3

        # Add Left Hand coordinates to history
        try:
            add_item_to_history(self.left_hand_coords_history, bodyresult.left_hand_tip, hand_coordinate_history_length)
        except AttributeError:
            add_item_to_history(self.left_hand_coords_history, Point3D(0, 0, 0), hand_coordinate_history_length)

        # Add Right hand coords to history
        try:
            add_item_to_history(self.right_hand_coords_history, bodyresult.right_hand_tip, hand_coordinate_history_length)
        except AttributeError:
            add_item_to_history(self.right_hand_coords_history, Point3D(0, 0, 0), hand_coordinate_history_length)

        hand_state_history_length = 7

        try:
            add_item_to_history(self.left_hand_state_history, bodyresult.left_hand_state, hand_state_history_length)
        except AttributeError:
            add_item_to_history(self.left_hand_state_history, HandState.UNTRACKED, hand_state_history_length)

        try:
            add_item_to_history(self.right_hand_state_history, bodyresult.right_hand_state, hand_state_history_length)
        except AttributeError:
            add_item_to_history(self.right_hand_state_history, HandState.UNTRACKED, hand_state_history_length)

    def process_bodyresult(self, bodyresult, message):
        """
        Method to process results of body tracking
        :param bodyresult: Result from bodytracking
        :param message: Message template for websocket connection
        :return: None
        """

        # update dictionary for infidata
        self.infodata["left"] = bodyresult.left_hand_state.name
        self.infodata["right"] = bodyresult.right_hand_state.name
        self.infodata["cut"] = self.__tracker_controller.minCutoff
        self.infodata["beta"] = self.__tracker_controller.beta

        # Detect where operator is pointing at
        right_handresult, left_handresult = self.process_hands(bodyresult, message)
        right_hand_pointing_to_screen, coords_r, intersect_point_r = right_handresult
        screen_x_r, screen_y_r = coords_r
        left_hand_pointing_to_screen, coords_l, intersect_point_l = left_handresult
        screen_x_l, screen_y_l = coords_l

        # Check if at least one hand is pointing to the screen.
        # If not, exit this method
        if not right_hand_pointing_to_screen and not left_hand_pointing_to_screen:
            self.right_hand_relative_pointing = False
            self.left_hand_relative_pointing = False
            self.reference_screen_point_for_rel_pointing= None
            self.reference_screenpos_for_rel_pointing = None
            self.reference_handpos_for_rel_pointing = None
            self.reference_screen_for_rel_pointing = None

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

        # Translate detected operations into touch screen API injections
        if self.touch_control_enabled:

            # use previous screen values for SELECT "tap" at location where user poitned at before action started
            if self.current_operation == Operation.SELECT_RIGHTHAND:
                screen_x_r, screen_y_r = self.prev_righthand_pointing
            if self.current_operation == Operation.SELECT_LEFTHAND:
                screen_x_l, screen_y_l = self.prev_lefthand_pointing

            self.process_transition(operation_transition, screen_x_l, screen_y_l, screen_x_r, screen_y_r)
            self.process_operation(screen_x_l, screen_y_l, screen_x_r, screen_y_r)

        self.prev_righthand_pointing = (screen_x_r, screen_y_r)
        self.prev_lefthand_pointing = (screen_x_l, screen_y_l)

    def process_hands(self, bodyresult: BodyResult, message: dict) -> tuple[tuple[bool, tuple[int, int], Point3D], tuple[bool, tuple[int, int], Point3D]]:
        """
        Detects where the user is pointing at on screen
        :param bodyresult: Result from body tracking
        :param message: Message dict to be sent to websocket server
        :return: Location of left and right hand wehre user is pointing at:
        Bool if pointing at all, tuple of ints with px-coordinates, point in 3d-space
        """

        # Get location where user is pointing at
        screen_r, hand_pointing_to_screen_r, coords_r, intersect_point_r = self.process_hand(Handednes.RIGHT, bodyresult, message)
        screen_l, hand_pointing_to_screen_l, coords_l, intersect_point_l = self.process_hand(Handednes.LEFT, bodyresult, message)

        if (hand_pointing_to_screen_r or self.right_hand_relative_pointing) and not hand_pointing_to_screen_l \
                and not self.left_hand_relative_pointing and bodyresult.left_hand.y < bodyresult.left_elbow.y:
            # Handle Slow (fine) pointing mode for right hand
            self.right_hand_relative_pointing = True
            if self.reference_screen_for_rel_pointing is None:
                self.reference_screen_for_rel_pointing = screen_r
            if self.reference_handpos_for_rel_pointing is None:
                self.reference_handpos_for_rel_pointing = bodyresult.right_hand
            if self.reference_screenpos_for_rel_pointing is None:
                self.reference_screenpos_for_rel_pointing = coords_r
            if self.reference_screen_point_for_rel_pointing is None:
                self.reference_screen_point_for_rel_pointing = intersect_point_r
            hand_pointing_to_screen_r, coords_r = self.handle_fine_pointing(bodyresult.pointer_start, bodyresult.pointer_end_right, message, "right")
        elif hand_pointing_to_screen_r:
            # Handle normal pointing mode for right hand
            self.right_hand_relative_pointing = False
            self.reference_screenpos_for_rel_pointing = None
            self.reference_handpos_for_rel_pointing = None
            self.reference_screen_for_rel_pointing = None
            self.reference_screen_point_for_rel_pointing = None
            coords_r = self.handle_coarse_pointing(coords_r, self.prev_righthand_pointing, message, "right")

        if (hand_pointing_to_screen_l or self.left_hand_relative_pointing) and not hand_pointing_to_screen_r \
                and not self.right_hand_relative_pointing and bodyresult.right_hand.y < bodyresult.left_elbow.y:
            # Handle Slow (fine) pointing mode for left hand
            self.left_hand_relative_pointing = True
            if self.reference_screen_for_rel_pointing is None:
                self.reference_screen_for_rel_pointing = screen_l
            if self.reference_handpos_for_rel_pointing is None:
                self.reference_handpos_for_rel_pointing = bodyresult.left_hand
            if self.reference_screenpos_for_rel_pointing is None:
                self.reference_screenpos_for_rel_pointing = coords_l
            if self.reference_screen_point_for_rel_pointing is None:
                self.reference_screen_point_for_rel_pointing = intersect_point_l
            hand_pointing_to_screen_l, coords_l = self.handle_fine_pointing(bodyresult.pointer_start, bodyresult.pointer_end_left, message, "left")
        elif hand_pointing_to_screen_l:
            # Handle normal pointing mode for left hand
            self.left_hand_relative_pointing = False
            self.reference_screenpos_for_rel_pointing = None
            self.reference_handpos_for_rel_pointing = None
            self.reference_screen_for_rel_pointing = None
            self.reference_screen_point_for_rel_pointing = None
            coords_l = self.handle_coarse_pointing(coords_l, self.prev_lefthand_pointing, message, "left")

        result_righthand = (hand_pointing_to_screen_r, coords_r, intersect_point_r)
        result_lefthand = (hand_pointing_to_screen_l, coords_l, intersect_point_l)

        return result_righthand, result_lefthand

    def process_hand(self, hand: Handednes, bodyresult: BodyResult, message: dict) -> tuple[Screen, bool, tuple[int, int], Point3D]:
        """
        Detects whether a user's arm is pointing at the screen
        :param hand: Hand which should be considered
        :param bodyresult: Result of body tracking
        :param message: Message to be sent through websocket server
        :return: Location where the hand is pointing:
        Screen that is pointed at, bool if pointing at all tupoe of ints with px-coordinates, point in 3d space
        """

        if hand == Handednes.INVALID:
            raise ValueError("hand value is INVALID. Must bei either LEFT or RIGHT")

        pointer = bodyresult.right_pointer if hand == Handednes.RIGHT else bodyresult.left_pointer
        msg_hand = "right" if hand == Handednes.RIGHT else "left"

        screen, screen_x, screen_y, intersect_point = self.get_screen_intersection(pointer)

        hand_pointing_to_screen = True
        if screen_x == -1 and screen_y == -1:
            hand_pointing_to_screen = False
            message[msg_hand]["present"] = False

        coords = (screen_x, screen_y)

        return screen, hand_pointing_to_screen, coords, intersect_point

    def get_screen_intersection(self, pointer: geom.Line) -> tuple[Screen, int, int, Point3D]:
        """
        Calculates location on screen where operator is pointing at.
        :param pointer: Line that is used to calculate intersection
        :return: Lcoation: Screen, px-coordiantes x and y, point in 3d-space
        """

        # Default values to be returned if no intersection occurs
        screen_id = -1
        screen_x, screen_y = -1, -1
        intersect_point = Point3D(-1, -1, -1)
        intersection_screen = Screen(-1,
                                     Point3D(-1, -1, -1),
                                     Point3D(1, 1, 1),
                                     1, 1)

        for screen in self.screens:
            # Calculate the point in 3D-space wehre pointer-line and infinite screen-plain intersect
            try:
                intersect_point_temp, behind = screen.screen_plain.intersect_line(pointer)
                if behind:
                    # dont consider if intersectino occurs behind the user
                    continue
            except geom.ParallelError:
                # dont consider if user poitns parallel to screen plaine
                continue

            # If line-plain intersection point is on screen, try-block is executed
            # If it is not, except block executes.
            try:
                screen_x, screen_y = screen.coords_to_px(intersect_point_temp)
                screen_id = screen.screen_id
                intersection_screen = screen
                intersect_point = intersect_point_temp
            except ValueError:
                continue

        # TODO: Properly calculate pixel position, do not hard-code them like done below

        # No intersection with any screen
        if screen_id == -1:
            return intersection_screen, -1, -1, intersect_point

        if screen_id == 0:
            return intersection_screen, 2 * 1920 + screen_x, screen_y, intersect_point

        if screen_id == 1:
            return intersection_screen, 1920 + screen_x, screen_y, intersect_point

        if screen_id == 2:
            return intersection_screen, 1920 - screen_x, screen_y, intersect_point

        if screen_id == 3:
            return intersection_screen, screen_x, screen_y, intersect_point

        if screen_id == 4:
            return intersection_screen, 960 + screen_x, screen_y, intersect_point

        return intersection_screen, -1, -1, intersect_point

    def handle_fine_pointing(self, pointer_start: Point3D, pointer_end: Point3D, message: dict, msg_hand: str) -> tuple[bool, tuple[int, int]]:
        """
        Method to handle the fine pointing mode.
        :param pointer_start: Point of body trackign where the pointer starts
        :param pointer_end: Point of body tracking where the pointer ends
        :param message: Message to be sent through websocket server
        :param msg_hand: name of hand that is currently processed for websocket
        :return: Updated location where user is pointing at: Bool value if pointing at screen, tuple of px-coordiantes
        """

        # Calcualte horizontal angle between reference poitn during relative pointing and current point
        h_pointer_start_screenpoint = Vector3D.from_points(
            Point3D(pointer_start.x, 0, pointer_start.z),
            Point3D(self.reference_screen_point_for_rel_pointing.x, 0, self.reference_screen_point_for_rel_pointing.z))
        h_pointer_start_end = Vector3D.from_points(
            Point3D(pointer_start.x, 0, pointer_start.z),
            Point3D(pointer_end.x, 0, pointer_end.z))
        h_sign = 1 if self.reference_handpos_for_rel_pointing.x < pointer_end.x else -1
        h_angle = h_pointer_start_screenpoint.get_angle(h_pointer_start_end) * h_sign

        # Calcualte vertical angle between reference poitn during relative pointing and current point
        v_pointer_start_screenpoint = Vector3D.from_points(
            Point3D(0, pointer_start.y, pointer_start.z),
            Point3D(0, self.reference_screen_point_for_rel_pointing.y, self.reference_screen_point_for_rel_pointing.z)
        )
        v_pointer_start_end = Vector3D.from_points(
            Point3D(0, pointer_start.y, pointer_start.z),
            Point3D(0, pointer_end.y, pointer_end.z)
        )
        v_sign = -1 if self.reference_handpos_for_rel_pointing.y > pointer_end.y else 1
        v_angle = v_pointer_start_screenpoint.get_angle(v_pointer_start_end) * v_sign

        # Calculate length of circle-segment that is covered relatively
        radius = pointer_start.distance(self.reference_screen_point_for_rel_pointing)
        h_segment_length = h_angle * radius
        v_segment_length = v_angle * radius

        # translate length of circle segment into new pixel coordinaets
        slowdown = 0.1
        dx = int(slowdown * h_segment_length * (self.reference_screen_for_rel_pointing.px_width / self.reference_screen_for_rel_pointing.screen_width))
        dy = int(slowdown * v_segment_length * (self.reference_screen_for_rel_pointing.px_height / self.reference_screen_for_rel_pointing.screen_height))

        screen_x = self.reference_screenpos_for_rel_pointing[0] + dx
        screen_y = self.reference_screenpos_for_rel_pointing[1] + dy

        pointing_to_screen = True if (0 <= screen_x < self.screen_total_width) and (0 <= screen_y <= self.screen_total_height) else False

        # Update data to be sent through websocket connection
        message[msg_hand]["present"] = pointing_to_screen
        message[msg_hand]["fine"] = True
        message[msg_hand]["position"]["x"] = screen_x
        message[msg_hand]["position"]["y"] = screen_y

        return pointing_to_screen, (screen_x, screen_y)

    def handle_coarse_pointing(self, coords: tuple[int, int], prev_coords: tuple[int, int], message: dict, msg_hand: str) -> tuple[int, int]:
        """
        Method to handle normal (absolute) pointing.
        :param coords: Coordinates where operator is currently pointing at
        :param prev_coords: Coordinates where operator pointed at previously
        :param message: Message to be sent through websocket server
        :param msg_hand: string to identify hand in websocket message. "left" or "right"
        :return: Updated px-coordinates ons creen where user is pointing at: Tuple of ints
        """

        screen_x, screen_y = coords
        prev_screen_x, prev_screen_y = prev_coords

        # prevent point jitter: if px-offset is <6 px compared to prev. frame, then use old values
        if abs(screen_x - prev_screen_x) < 5:
            screen_x = prev_screen_x
        if abs(screen_y - prev_screen_y) < 5:
            screen_y = prev_screen_y

        # Update message for websocket server
        message[msg_hand]["present"] = True
        message[msg_hand]["fine"] = False
        message[msg_hand]["position"]["x"] = screen_x
        message[msg_hand]["position"]["y"] = screen_y

        coords = (screen_x, screen_y)

        return coords

    def detect_operation_handstate(self, bodyresult: BodyResult, left_pointing: bool, right_pointing: bool, intersect_point_l: Point3D, intersect_point_r: Point3D) -> Operation:
        """
        Detects the operation the user is currently performing
        :param bodyresult: Result of body tracking
        :param left_pointing: Bool if users left hand is pointing to screen
        :param right_pointing: Bool if users right hand is pointing to screen
        :param intersect_point_l: 3D-point where users left hand is pointing at
        :param intersect_point_r: 3D-point where users right hand is pointing at
        :return: Operation that was detected
        """

        # get majority handstate of last x frames from hand_state_history
        right_hand_state, _ = Counter(self.right_hand_state_history).most_common()[0]
        left_hand_state, _ = Counter(self.left_hand_state_history).most_common()[0]

        # Detect ZOOM operation
        if left_pointing and right_pointing and right_hand_state == HandState.CLOSED and left_hand_state == HandState.CLOSED:
            return Operation.ZOOM

        # Detect SELECT Operation (contains legacy one-hand operation code)
        if self.interaction_mechanism == InteractionMechanism.SELECT_RIGHT_PAN_LEFT or self.interaction_mechanism == InteractionMechanism.SELECT_BOTH_PAN_BOTH:
            if right_pointing and self.detect_righthand_selection(bodyresult, intersect_point_r):
                return Operation.SELECT_RIGHTHAND
            if left_hand_state == HandState.CLOSED and left_pointing:
                return Operation.PAN_LEFTHAND

        # Detect SELECT Operation (contains legacy one-hand operation code)
        if self.interaction_mechanism == InteractionMechanism.SELECT_LEFT_PAN_RIGHT or self.interaction_mechanism == InteractionMechanism.SELECT_BOTH_PAN_BOTH:
            if left_pointing and self.detect_lefthand_selection(bodyresult, intersect_point_l):
                return Operation.SELECT_LEFTHAND
            if right_hand_state == HandState.CLOSED and right_pointing:
                return Operation.PAN_RIGHTHAND

        return Operation.IDLE

    def detect_righthand_selection(self, bodyresult: BodyResult, intersection_point_r: Point3D) -> bool:
        """
        Detects right hand selection
        :param bodyresult: Bodytracking result
        :param intersection_point_r: Point in 3d where right hand intersects the screen
        :return: Bool value if righthand selection was detected
        """

        if bodyresult.right_hand_state == HandState.CLOSED or bodyresult.left_hand_state == HandState.CLOSED:
            return False

        # TODO: HANDLE THIS FOR multiscree setup (?)
        # Check if each hand point in history is closer to camera than the one before
        intersection_point_r_plaine = Point3D(intersection_point_r.x, 0, intersection_point_r.z)
        for idx in range(len(self.right_hand_coords_history) - 1):
            current_plaine = Point3D(self.right_hand_coords_history[idx].x, 0, self.right_hand_coords_history[idx].z)
            next_plaine = Point3D(self.right_hand_coords_history[idx+1].x, 0, self.right_hand_coords_history[idx+1].z)
            if current_plaine.distance(intersection_point_r_plaine) <= next_plaine.distance(intersection_point_r_plaine):
                return False

        oldest = self.right_hand_coords_history[0]
        latest = self.right_hand_coords_history[-1]

        # keep hand at about the same height
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
        """
        Detects left hand selection
        :param bodyresult: Body tracking result
        :param intersection_point_l: Point in 3d wehre left hand intersects the screen
        :return: Bool value if lefthand selection was detected
        """

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
        """
        Properly perform transition between operations
        :param transition: Transition to be performed
        :param x_left: X-Coordniate on screen where user is pointing at with left hand
        :param y_left: Y-Coordinate on screen where user is pointing at with left hand
        :param x_right: X-Coordinate on screen wher euser is pointing at with right hand
        :param y_right: Y-Coordinate on screen wher euser is pointing at with right hand
        :return: None
        """
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
            # Do not transtino to panleft, can lead to false selection easily
            # Reason: One hand from zoom is released slightly earlier than other -> interpreted as tap -> selection
            #self.transition_to_panleft(x_left, y_left)
            return
        if transition == OperationTransition.ZOOM_TO_PANRIGHT:
            self.transition_from_zoom()
            # Do not transtino to panleft, can lead to false selection easily
            # Reason: One hand from zoom is released slightly earlier than other -> interpreted as tap -> selection
            #self.transition_to_panrigth(x_right, y_right)
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
        """ Transitions to pan-left operation: Emulates fingerperss on tuoch screen. """
        tc.finger_down((self.screen_total_width - x_left, y_left))

    def transition_from_panleft(self):
        """ Ends Pan-Left operation: Emulates lifting finger up from touch screen. """
        tc.finger_up()
        self.last_tap = time()

    def transition_to_panrigth(self, x_right: int, y_right: int):
        """ Transitions to pan-right operation: Emulates fingerperss on tuoch screen. """
        tc.finger_down((self.screen_total_width - x_right, y_right))

    def transition_from_panright(self):
        """ Ends Pan-Left operation: Emulates lifting finger up from touch screen. """
        tc.finger_up()
        self.last_tap = time()

    def transition_from_zoom(self):
        tc.two_fingers_up()
        self.last_tap = time()

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