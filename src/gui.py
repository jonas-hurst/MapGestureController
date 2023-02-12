from guibaseExtended import GuibaseExtended, CalibrateDialogExtended
from cameracontrol import *
from screen import Screen
import geom
from websocketserver import Server
from constants import *
import touchcontrol as tc


class MainWindow(GuibaseExtended):
    def __init__(self, parent):
        GuibaseExtended.__init__(self, parent)

        self.screen = Screen(0,
                             geom.Point3D(-1100, -1150, -340),
                             geom.Point3D(1100, 130, -340),
                             1920, 1080)

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

        screen_x_r, screen_y_r = self.get_screen_intersection(bodyresult.right_pointer)
        if screen_x_r == -1 and screen_y_r == -1:
            message["right"]["present"] = False
        else:
            message["right"]["present"] = True
            message["right"]["position"]["x"] = screen_x_r
            message["right"]["position"]["y"] = screen_y_r

        screen_x_l, screen_y_l = self.get_screen_intersection(bodyresult.left_pointer)
        if screen_x_l == -1 and screen_y_l == -1:
            message["left"]["present"] = False
        else:
            message["left"]["present"] = True
            message["left"]["position"]["x"] = screen_x_l
            message["left"]["position"]["y"] = screen_y_l

        if screen_x_r == -1 and screen_y_r == -1 and screen_x_l == -1 and screen_y_l == -1:
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
        try:
            pnt = self.screen.screen_plain.intersect_line(pointer)
        except geom.ParallelError:
            print("PARALLEL ERROR")
            return -1, -1

        # If line-plain intersection point is on screen, try-block is executed
        # If it is not, except block executes.
        try:
            screen_x, screen_y = self.screen.coords_to_px(pnt)

        except ValueError:
            return -1, -1

        return screen_x, screen_y

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
        active_dist = 400
        dist_nose_right = bodyresult.nose.distance(bodyresult.right_hand)
        dist_nose_left = bodyresult.nose.distance(bodyresult.left_hand)
        if dist_nose_right > active_dist and right_pointing and not left_pointing:
            return Operation.PAN_RIGHTHAND
        if dist_nose_left > active_dist and left_pointing and not right_pointing:
            return Operation.PAN_LEFTHAND
        if left_pointing and right_pointing and dist_nose_right > active_dist and dist_nose_left > active_dist:
            return Operation.ZOOM
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
            return
        if transition == OperationTransition.PANLEFT_TO_PANRIGHT:
            return
        if transition == OperationTransition.PANLEFT_TO_ZOOM:
            return
        if transition == OperationTransition.PANLEFT_TO_POINTING:
            return
        if transition == OperationTransition.PANLEFT_TO_IDLE:
            return
        if transition == OperationTransition.PANRIGHT_TO_SELECT:
            tc.finger_up()
            return
        if transition == OperationTransition.PANRIGHT_TO_PANLEFT:
            tc.finger_up()
            return
        if transition == OperationTransition.PANRIGHT_TO_ZOOM:
            tc.finger_up()
            return
        if transition == OperationTransition.PANRIGHT_TO_POINTING:
            tc.finger_up()
            return
        if transition == OperationTransition.PANRIGHT_TO_IDLE:
            tc.finger_up()
            return
        if transition == OperationTransition.ZOOM_TO_SELECT:
            return
        if transition == OperationTransition.ZOOM_TO_PANLEFT:
            return
        if transition == OperationTransition.ZOOM_TO_PANRIGHT:
            return
        if transition == OperationTransition.ZOOM_TO_POINTING:
            return
        if transition == OperationTransition.ZOOM_TO_IDLE:
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
            return
        if transition == OperationTransition.IDLE_TO_PANRIGHT:
            tc.finger_down((1920 - x_right, y_right))
            self.prev_righthand_pointing = (x_right, y_right)
            return
        if transition == OperationTransition.IDLE_TO_ZOOM:
            return
        if transition == OperationTransition.IDLE_TO_POINTING:
            return

    def process_operation(self, x_left: int, y_left: int, x_right: int, y_right: int):
        if self.current_operation == Operation.PAN_RIGHTHAND:
            self.pan_righthand(x_right, y_right)

    def pan_righthand(self, x: int, y: int):
        tc.move_finger((self.prev_righthand_pointing[0]-x, y - self.prev_righthand_pointing[1]))
        self.prev_righthand_pointing = (x, y)

    def pan_lefthand(self, x: int, y: int):
        pass

    def zoom(self):
        pass


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
