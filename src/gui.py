from guibaseExtended import GuibaseExtended
import threading
from cameracontrol import TrackerController


class MainWindow(GuibaseExtended):
    def __init__(self, parent):
        GuibaseExtended.__init__(self, parent)

        self.__tracker_controller = TrackerController(visualize=True)

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

    def start_camera(self):
        camera_thread = threading.Thread(target=self.cameraloop, daemon=True)
        self.__tracker_controller.initialize_tracking()
        camera_thread.start()

    def stop_camera(self):
        self.__tracker_controller.camera_running = False
        self.__tracker_controller.stopDevice()

    def cameraloop(self):
        while True:
            self.__tracker_controller.captureFrame()
            self.set_bitmap(self.__tracker_controller.color_image_bgr)

            infodata = {"fps": self.__tracker_controller.fps,
                        "bodies": self.__tracker_controller.number_tracked_bodies}
            self.set_datagrid_values(infodata)

            bodyinfo = None
            if self.__tracker_controller.number_tracked_bodies == 1:
                print(1)
            else:
                print("more")

            if not self.__tracker_controller.camera_running:
                break
