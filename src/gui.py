import wx

from guibaseExtended import GuibaseExtended, ImagePanel
import threading
from mpTest2 import GestureController


class MainWindow(GuibaseExtended):
    def __init__(self, parent):
        GuibaseExtended.__init__(self, parent)

        self.__gesture_controller = GestureController(visualize=True)

    def on_tgl_camera( self, event ):
        btn_value = self.tgl_btn_start_camera.Value
        if btn_value:
            self.start_camera()
        else:
            self.stop_camera()

    def on_close( self, event ):
        if self.__gesture_controller.camera_running:
            self.stop_camera()
        wx.Exit()


    def start_camera( self ):
        camera_thread = threading.Thread(target=self.cameraloop, daemon=True)
        self.__gesture_controller.initialize_tracking()
        camera_thread.start()

    def stop_camera(self):
        self.__gesture_controller.camera_running = False
        self.__gesture_controller.stopDevice()

    def cameraloop(self):
        while True:
            self.__gesture_controller.captureFrame()
            self.img_panel.set_bitmap(self.__gesture_controller.color_image_bgr)
            if not self.__gesture_controller.camera_running:
                break

