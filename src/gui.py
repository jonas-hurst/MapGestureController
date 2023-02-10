import math

from guibaseExtended import GuibaseExtended, CalibrateDialogExtended
from cameracontrol import *
from screen import Screen
import geom
from websocketserver import Server
from constants import *


class MainWindow(GuibaseExtended):
    def __init__(self, parent):
        GuibaseExtended.__init__(self, parent)

        self.screen = Screen(0,
                             geom.Point3D(-1100, -1150, -340),
                             geom.Point3D(1100, 130, -340),
                             1920, 1080)

        self.__tracker_controller = TrackerController(visualize=True)

        self.prev_righthand_point = None
        self.prev_lefthand_point = None

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
                        "cut": 0,
                        "beta": 0}

            if bodyresult is not None:
                self.process_bodyresult(bodyresult, server, message, infodata)

            self.set_datagrid_values(infodata)

            if not self.__tracker_controller.camera_running:
                break

        server.close_server()

    def process_bodyresult(self, bodyresult, server, message, infodata):
        infodata["left"] = bodyresult.left_hand_state
        infodata["right"] = bodyresult.right_hand_state
        infodata["cut"] = self.__tracker_controller.minCutoff
        infodata["beta"] = self.__tracker_controller.beta

        # Calculate the point in 3D-space wehre pointer-line and infinite screen-plain intersect
        # A check whether this point is on screen occurs later
        # TODO: Properly handle ParallelError, e.g. set pnt(0,0,0)
        try:
            pnt_right = self.screen.screen_plain.intersect_line(bodyresult.right_pointer)
        except geom.ParallelError:
            return
        try:
            pnt_left = self.screen.screen_plain.intersect_line(bodyresult.left_pointer)
        except geom.ParallelError:
            return

        # If line-plain intersection point is on screen, try-block is executed
        # If it is not, except block executes.
        try:
            # print(self.screen.coords_to_px(pnt))
            x_r, y_r = self.screen.coords_to_px(pnt_right)
            message["right"]["present"] = True
            message["right"]["position"]["x"] = x_r
            message["right"]["position"]["y"] = y_r
        except ValueError:
            message["right"]["present"] = False

        try:
            x_l, y_l = self.screen.coords_to_px(pnt_left)
            message["left"]["present"] = True
            message["left"]["position"]["x"] = x_l
            message["left"]["position"]["y"] = y_l
        except ValueError:
            message["left"]["present"] = False

        # TODO: behavior if xr, yr, xl, yl are not assigned

        operation: Operation = self.detect_operation(bodyresult)
        if operation == Operation.PAN_RIGHTHAND:
            self.pan_righthand(x_r, y_r)
        if operation == Operation.PAN_LEFTHAND:
            self.pan_lefthand(x_l, y_l)
        if operation == Operation.ZOOM:
            self.zoom()

        server.send_json(message)

    def detect_operation(self, bodyresult: BodyResult) -> Operation:
        if bodyresult.right_hand_state == HandState.CLOSED and bodyresult.left_hand_state != HandState.CLOSED:
            return Operation.PAN_RIGHTHAND
        if bodyresult.left_hand_state == HandState.CLOSED and bodyresult.right_hand_state != HandState.CLOSED:
            return Operation.PAN_LEFTHAND
        if bodyresult.left_hand_state == HandState.CLOSED and bodyresult.right_hand_state == HandState.CLOSED:
            return Operation.ZOOM

    def pan_righthand(self, x: int, y: int):
        if self.prev_righthand_point is None:
            self.prev_righthand_point = (x, y)

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
