from guibaseExtended import GuibaseExtended, CalibrateDialogExtended
from cameracontrol import *
from screen import *
import geom
from websocketserver import Server
from constants import *
import touchcontrol as tc


class MainWindow(GuibaseExtended):
    def __init__(self, parent):
        GuibaseExtended.__init__(self, parent)

        self.screens = SCREEN_SINGLE_ABOVE

        self.screen_total_width = sum([screen.px_width for screen in self.screens])

        self.touch_control_enabled = False

        self.__tracker_controller = TrackerController(visualize=True)

        self.infodata: dict = self.initialize_infodata()
        self.set_datagrid_values(self.infodata)

        self.current_operation: Operation = Operation.IDLE  # Operation performed in the current frame
        self.previous_operation: Operation = Operation.IDLE  # Operation performed in the alst frame

        self.prev_lefthand_pointing = None
        self.left_hand_state_history = []
        self.prev_righthand_pointing = None
        self.right_hand_state_history = []

    def on_tgl_camera(self, event):
        btn_value = self.tgl_btn_start_camera.Value
        if btn_value:
            self.start_camera()
        else:
            self.stop_camera()
        GuibaseExtended.on_tgl_camera(self, event)

    def on_tgl_touchcontrol(self, event):
        self.touch_control_enabled = self.tgl_btn_touchcontrol.Value

    def on_close(self, event):
        if self.__tracker_controller.camera_running:
            self.stop_camera()
        GuibaseExtended.on_close(self, event)

    def on_calibrate(self, event):
        dlg = CalibrateDialogWindow(self,
                                    self.__tracker_controller.tune_filters,
                                    self.__tracker_controller.minCutoff,
                                    self.__tracker_controller.beta)
        dlg.ShowModal()

    def initialize_infodata(self) -> dict:
        d = {"fps": 0,
             "bodies": "n.a.",
             "pitch": "n.a.",
             "roll": "n.a.",
             "left": HandState.UNTRACKED.name,
             "right": HandState.UNTRACKED.name,
             "operation": Operation.IDLE.name,
             "cut": 0,
             "beta": 0}
        return d

    def start_camera(self):
        camera_thread = threading.Thread(target=self.cameraloop, daemon=True)
        self.__tracker_controller.initialize_tracking()
        camera_thread.start()

    def stop_camera(self):
        self.__tracker_controller.camera_running = False
        self.__tracker_controller.stopDevice()

    def cameraloop(self):
        server = Server()
        server.open_server()

        message = {
            "right": {
                "present": False,
                "position": {
                    "x": 0,
                    "y": 0
                }
            },
            "left": {
                "present": False,
                "position": {
                    "x": 0,
                    "y": 0
                }
            }
        }

        while True:
            bodyresult: BodyResult = self.__tracker_controller.getBodyCaptureData()
            self.set_bitmap(self.__tracker_controller.color_image_rgb)

            self.infodata["fps"] = self.__tracker_controller.fps
            self.infodata["bodies"] = self.__tracker_controller.number_tracked_bodies
            self.infodata["pitch"] = round(self.__tracker_controller.pitch * (180 / math.pi), 1)
            self.infodata["roll"] = round(self.__tracker_controller.roll * (180 / math.pi), 1)

            # Add Left Hand state to history
            if len(self.left_hand_state_history) > 5:
                self.left_hand_state_history.pop()
            try:
                self.left_hand_state_history.append(bodyresult.left_hand_state)
            except AttributeError:
                self.left_hand_state_history.append(HandState.UNTRACKED)

            # Add Right hand state to history
            if len(self.right_hand_state_history) > 5:
                self.right_hand_state_history.pop()
            try:
                self.right_hand_state_history.append(bodyresult.right_hand_state)
            except AttributeError:
                self.right_hand_state_history.append(HandState.UNTRACKED)

            if bodyresult is not None:
                self.process_bodyresult(bodyresult, message)
            else:
                message["right"]["present"] = False
                message["left"]["present"] = False
                tc.finger_up()
                self.prev_righthand_pointing = None
                self.prev_lefthand_pointing = None

            self.infodata["operation"] = self.current_operation.name

            server.send_json(message)
            self.set_datagrid_values(self.infodata)

            if not self.__tracker_controller.camera_running:
                break

        server.close_server()

    def process_bodyresult(self, bodyresult, message):
        self.infodata["left"] = bodyresult.left_hand_state.name
        self.infodata["right"] = bodyresult.right_hand_state.name
        self.infodata["cut"] = self.__tracker_controller.minCutoff
        self.infodata["beta"] = self.__tracker_controller.beta

        # Check if Right hand is pointing towards the screen
        screen_x_r, screen_y_r = self.get_screen_intersection(bodyresult.right_pointer)
        right_hand_pointing_to_screen = False
        if screen_x_r == -1 and screen_y_r == -1:
            message["right"]["present"] = False
            self.prev_righthand_pointing = None
        else:
            message["right"]["present"] = True
            message["right"]["position"]["x"] = screen_x_r
            message["right"]["position"]["y"] = screen_y_r
            right_hand_pointing_to_screen = True

        # Check if Left hand is pointing towards the screen
        screen_x_l, screen_y_l = self.get_screen_intersection(bodyresult.left_pointer)
        left_hand_pointing_to_screen = False
        if screen_x_l == -1 and screen_y_l == -1:
            message["left"]["present"] = False
            self.prev_lefthand_pointing = None
        else:
            message["left"]["present"] = True
            message["left"]["position"]["x"] = screen_x_l
            message["left"]["position"]["y"] = screen_y_l
            left_hand_pointing_to_screen = True

        # Check if at least one hand is pointing to the screen.
        # If not, exit this method
        if not right_hand_pointing_to_screen and not left_hand_pointing_to_screen:
            self.previous_operation = self.current_operation
            self.current_operation = Operation.IDLE
            return

        # After here only if if hand points to screen is on screen
        self.previous_operation = self.current_operation
        # self.current_operation = self.detect_operation_handstate(bodyresult)
        self.current_operation = self.detect_operation_distance(bodyresult, left_hand_pointing_to_screen, right_hand_pointing_to_screen)

        operation_transition: OperationTransition = self.get_operation_transition()

        if self.touch_control_enabled:
            self.process_transition(operation_transition, screen_x_l, screen_y_l, screen_x_r, screen_y_r)
            self.process_operation(screen_x_l, screen_y_l, screen_x_r, screen_y_r)

    def get_screen_intersection(self, pointer: geom.Line) -> tuple[int, int]:
        # Calculate the point in 3D-space wehre pointer-line and infinite screen-plain intersect
        # A check whether this point is on screen occurs later
        screen_id = -1
        for screen in self.screens:
            try:
                pnt = screen.screen_plain.intersect_line(pointer)
            except geom.ParallelError:
                continue

            # If line-plain intersection point is on screen, try-block is executed
            # If it is not, except block executes.
            try:
                screen_x, screen_y = screen.coords_to_px(pnt)
                screen_id = screen.screen_id
            except ValueError:
                continue

        # TODO: Properly calculate screen coordinates
        # Currently, this is hard-coded to specific setups

        # No intersection with any screen
        if screen_id == -1:
            return -1, -1

        if screen_id == 0:
            return 2 * 1920 + screen_x, screen_y

        if screen_id == 1:
            return 1920 + screen_x, screen_y

        if screen_id == 2:
            return 1920 - screen_x, screen_y

        if screen_id == 3:
            return screen_x, screen_y

        print(screen_id)
        # return screen_x, screen_y
        return -1, -1

    def detect_operation_handstate(self, bodyresult: BodyResult) -> Operation:
        # if bodyresult.right_hand_state == HandState.CLOSED and bodyresult.left_hand_state != HandState.CLOSED:
        #     return Operation.PAN_RIGHTHAND
        # if bodyresult.left_hand_state == HandState.CLOSED and bodyresult.right_hand_state != HandState.CLOSED:
        #     return Operation.PAN_LEFTHAND
        # if bodyresult.left_hand_state == HandState.CLOSED and bodyresult.right_hand_state == HandState.CLOSED:
        #     return Operation.ZOOM
        if bodyresult.right_hand_state == HandState.CLOSED:
            return Operation.PAN_RIGHTHAND
        return Operation.IDLE

    def detect_operation_distance(self, bodyresult: BodyResult, left_pointing: bool, right_pointing: bool) -> Operation:
        """
        Detect an operation based on distance of hand to something
        :param bodyresult: object containing results from bodytracking
        :param left_pointing: Bool Value indicating if left hand is pointing to screen
        :param right_pointing: Bool Value indicating if right hand is pointing to screen
        :return: The detected Operation
        """
        active_dist = 400
        dist_nose_right = bodyresult.chest.distance(bodyresult.right_hand)
        dist_nose_left = bodyresult.chest.distance(bodyresult.left_hand)
        if left_pointing and right_pointing and dist_nose_right > active_dist and dist_nose_left > active_dist:
            return Operation.ZOOM
        if dist_nose_right > active_dist and right_pointing:
            return Operation.PAN_RIGHTHAND
        if dist_nose_left > active_dist and left_pointing:
            return Operation.PAN_LEFTHAND
        return Operation.IDLE

    def get_operation_transition(self) -> OperationTransition:
        """
        Method to determine the appropriate transition between operations
        :return: Transition between operations
        """
        if self.previous_operation == self.current_operation:
            return OperationTransition.REMAINS

        if self.previous_operation == Operation.SELECT:
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.SELECT_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.SELECT_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.SELECT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.SELECT_TO_IDLE

        if self.previous_operation == Operation.PAN_LEFTHAND:
            if self.current_operation == Operation.SELECT:
                return OperationTransition.PANLEFT_TO_SELECT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.PANLEFT_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.PANLEFT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.PANLEFT_TO_IDLE

        if self.previous_operation == Operation.PAN_RIGHTHAND:
            if self.current_operation == Operation.SELECT:
                return OperationTransition.PANRIGHT_TO_SELECT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.PANRIGHT_TO_PANLEFT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.PANRIGHT_TO_ZOOM
            if self.current_operation == Operation.IDLE:
                return OperationTransition.PANRIGHT_TO_IDLE

        if self.previous_operation == Operation.ZOOM:
            if self.current_operation == Operation.SELECT:
                return OperationTransition.ZOOM_TO_SELECT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.ZOOM_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.ZOOM_TO_PANRIGHT
            if self.current_operation == Operation.IDLE:
                return OperationTransition.ZOOM_TO_IDLE

        if self.previous_operation == Operation.IDLE:
            if self.current_operation == Operation.SELECT:
                return OperationTransition.IDLE_TO_SELECT
            if self.current_operation == Operation.PAN_LEFTHAND:
                return OperationTransition.IDLE_TO_PANLEFT
            if self.current_operation == Operation.PAN_RIGHTHAND:
                return OperationTransition.IDLE_TO_PANRIGHT
            if self.current_operation == Operation.ZOOM:
                return OperationTransition.IDLE_TO_ZOOM

    def process_transition(self, transition: OperationTransition, x_left: int, y_left: int, x_right: int, y_right: int):
        if transition == OperationTransition.REMAINS:
            return
        if transition == OperationTransition.SELECT_TO_PANLEFT:
            return
        if transition == OperationTransition.SELECT_TO_PANRIGHT:
            return
        if transition == OperationTransition.SELECT_TO_ZOOM:
            return
        if transition == OperationTransition.SELECT_TO_POINTING:
            return
        if transition == OperationTransition.SELECT_TO_IDLE:
            return
        if transition == OperationTransition.PANLEFT_TO_SELECT:
            self.transition_from_panleft()
            return
        if transition == OperationTransition.PANLEFT_TO_PANRIGHT:
            self.transition_from_panleft()
            return
        if transition == OperationTransition.PANLEFT_TO_ZOOM:
            self.transition_from_panleft()
            self.transition_to_zoom(x_left, y_left, x_right, y_right)
            return
        if transition == OperationTransition.PANLEFT_TO_POINTING:
            self.transition_from_panleft()
            return
        if transition == OperationTransition.PANLEFT_TO_IDLE:
            self.transition_from_panleft()
            return
        if transition == OperationTransition.PANRIGHT_TO_SELECT:
            self.transition_from_panright()
            return
        if transition == OperationTransition.PANRIGHT_TO_PANLEFT:
            self.transition_from_panright()
            return
        if transition == OperationTransition.PANRIGHT_TO_ZOOM:
            self.transition_from_panright()
            self.transition_to_zoom(x_left, y_left, x_right, y_right)
            return
        if transition == OperationTransition.PANRIGHT_TO_POINTING:
            self.transition_from_panright()
            return
        if transition == OperationTransition.PANRIGHT_TO_IDLE:
            self.transition_from_panright()
            return
        if transition == OperationTransition.ZOOM_TO_SELECT:
            return
        if transition == OperationTransition.ZOOM_TO_PANLEFT:
            self.transition_from_zoom()
            self.transition_to_panleft(x_left, y_left)
            return
        if transition == OperationTransition.ZOOM_TO_PANRIGHT:
            self.transition_from_zoom()
            self.transition_to_panrigth(x_right, y_right)
            return
        if transition == OperationTransition.ZOOM_TO_POINTING:
            self.transition_from_zoom()
            return
        if transition == OperationTransition.ZOOM_TO_IDLE:
            self.transition_from_zoom()
            return
        if transition == OperationTransition.POINTING_TO_SELECT:
            return
        if transition == OperationTransition.POINTING_TO_PANLEFT:
            return
        if transition == OperationTransition.POINTING_TO_PANRIGHT:
            return
        if transition == OperationTransition.POINTING_TO_ZOOM:
            return
        if transition == OperationTransition.IDLE_TO_SELECT:
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
        if transition == OperationTransition.IDLE_TO_POINTING:
            return

    def transition_to_panleft(self, x_left: int, y_left: int):
        tc.finger_down((self.screen_total_width - x_left, y_left))
        self.prev_lefthand_pointing = (x_left, y_left)

    def transition_from_panleft(self):
        tc.finger_up()
        self.prev_lefthand_pointing = None

    def transition_to_panrigth(self, x_right: int, y_right: int):
        tc.finger_down((self.screen_total_width - x_right, y_right))
        self.prev_righthand_pointing = (x_right, y_right)

    def transition_from_panright(self):
        tc.finger_up()
        self.prev_righthand_pointing = None

    def transition_from_zoom(self):
        tc.two_fingers_up()
        self.prev_righthand_pointing = None
        self.prev_lefthand_pointing = None

    def transition_to_zoom(self, x_left, y_left, x_right, y_right):
        tc.two_fingers_down((self.screen_total_width - x_left, y_left), (self.screen_total_width - x_right, y_right))
        self.prev_righthand_pointing = (x_right, y_right)
        self.prev_lefthand_pointing = (x_left, y_left)

    def process_operation(self, x_left: int, y_left: int, x_right: int, y_right: int):
        if self.current_operation == Operation.PAN_RIGHTHAND:
            self.pan_righthand(x_right, y_right)

        if self.current_operation == Operation.PAN_LEFTHAND:
            self.pan_lefthand(x_left, y_left)

        if self.current_operation == Operation.ZOOM:
            self.zoom(x_left, y_left, x_right, y_right)

    def pan_righthand(self, x: int, y: int):
        if self.prev_righthand_pointing is None:
            self.prev_righthand_pointing = (self.screen_total_width - x, y)
        tc.move_finger((self.prev_righthand_pointing[0]-x, y - self.prev_righthand_pointing[1]))
        self.prev_righthand_pointing = (x, y)

    def pan_lefthand(self, x: int, y: int):
        if self.prev_lefthand_pointing is None:
            self.prev_lefthand_pointing = (self.screen_total_width - x, y)
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


class CalibrateDialogWindow(CalibrateDialogExtended):
    def __init__(self, parent, tunefunction, cutoff, beta):
        CalibrateDialogExtended.__init__(self, parent)

        self.tuneunction = tunefunction

        self.slider_mincutoff.SetValue(int(cutoff * 100000))
        self.slider_beta.SetValue(int(beta * 100))

    def on_okay(self, event):
        self.Close()

    def on_slider_changed(self, event):
        beta_value = self.slider_beta.GetValue() / 100
        mincutoff_value = self.slider_mincutoff.GetValue() / 100000
        self.tuneunction(min_cutoff=mincutoff_value, beta=beta_value)
