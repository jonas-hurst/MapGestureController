from guibase import Guibase
import threading
from mpTest2 import GestureController


class MainWindow(Guibase):
    def __init__(self, parent):
        Guibase.__init__(self, parent)

        self.__gesture_controller = GestureController()
        self.__camera_thread = threading.Thread(target=self.__gesture_controller.start_cameraloop, daemon=True)

    def on_start_camera( self, event ):
        value: bool = self.tgl_btn_start_camera.Value

        if value:
            self.__camera_thread.start()
        else:
            print("stopping camera not implemented. Press q to stop")
