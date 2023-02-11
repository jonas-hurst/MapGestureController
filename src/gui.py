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

        self.__tracker_controller = TrackerController(visualize=True)

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

            infodata = {"fps": self.__tracker_controller.fps,
                        "bodies": self.__tracker_controller.number_tracked_bodies,
                        "pitch": round(self.__tracker_controller.pitch * (180 / math.pi), 1),
                        "roll": round(self.__tracker_controller.roll * (180 / math.pi), 1),
                        "left": 0,
                        "right": 0,
                        "operation": 0,
                        "cut": 0,
                        "beta": 0}

            # Add Left Hand state to history
            if len(self.left_hand_state_history) > 10:
                self.left_hand_state_history.pop()
            try:
                self.left_hand_state_history.append(bodyresult.left_hand_state)
            except AttributeError:
                self.left_hand_state_history.append(HandState.UNTRACKED)

            # Add Right hand state to history
            if len(self.right_hand_state_history) > 10:
                self.right_hand_state_history.pop()
            try:
                self.right_hand_state_history.append(bodyresult.right_hand_state)
            except AttributeError:
                self.right_hand_state_history.append(HandState.UNTRACKED)

            if bodyresult is not None:
                self.process_bodyresult(bodyresult, server, message, infodata)
            else:
                message["right"]["present"] = False
                message["left"]["present"] = False
                tc.finger_up()
                self.prev_righthand_pointing = None

            server.send_json(message)
            self.set_datagrid_values(infodata)

            if not self.__tracker_controller.camera_running:
                break

        server.close_server()

    def process_bodyresult(self, bodyresult, server, message, infodata):
        infodata["left"] = bodyresult.left_hand_state.name
        infodata["right"] = bodyresult.right_hand_state.name
        infodata["cut"] = self.__tracker_controller.minCutoff
        infodata["beta"] = self.__tracker_controller.beta

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
            return

        # After here only if if hand points to screen is on screen
        operation: Operation = self.detect_operation(bodyresult)
        infodata["operation"] = operation.name

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

    def detect_operation(self, bodyresult: BodyResult) -> Operation:
        if bodyresult.right_hand_state == HandState.CLOSED and bodyresult.left_hand_state != HandState.CLOSED:
            return Operation.PAN_RIGHTHAND
        if bodyresult.left_hand_state == HandState.CLOSED and bodyresult.right_hand_state != HandState.CLOSED:
            return Operation.PAN_LEFTHAND
        if bodyresult.left_hand_state == HandState.CLOSED and bodyresult.right_hand_state == HandState.CLOSED:
            return Operation.ZOOM
        return Operation.IDLE

    def pan_righthand(self, x: int, y: int):
        if self.prev_righthand_pointing is None:
            self.prev_righthand_pointing = (x, y)
            tc.finger_down((x, y))
            print("engage")
        else:
            print("moving")
            tc.move_finger((1920 - (self.prev_righthand_pointing[0]-x), self.prev_righthand_pointing[1]-y))

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
