import wx
from guibase import Guibase
import threading
from mpTest2 import TrackerController
import numpy as np
from cv2 import resize,cvtColor, COLOR_BGR2RGB


class MainWindow(Guibase):
    def __init__(self, parent):
        Guibase.__init__(self, parent)

        width, height = 854, 480

        frame = np.zeros((width, height, 3))
        self.bmp = wx.Bitmap.FromBuffer(width, height, frame)
        self.image_container.SetInactiveBitmap(self.bmp)
        self.image_container.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.__tracker_controller = TrackerController(visualize=True)

    def on_tgl_camera( self, event ):
        btn_value = self.tgl_btn_start_camera.Value
        if btn_value:
            self.start_camera()
        else:
            self.stop_camera()
        self.tgl_btn_show_feed.Enable(btn_value)
        self.tgl_btn_touchcontrol.Enable(btn_value)

    def on_close( self, event ):
        if self.__tracker_controller.camera_running:
            self.stop_camera()
        wx.Exit()

    def start_camera( self ):
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
            if not self.__tracker_controller.camera_running:
                break

    def set_bitmap(self, frame):
        frame_small = resize(frame.copy(), (854, 480))
        frame_small_rgb = cvtColor(frame_small, COLOR_BGR2RGB)
        self.bmp.CopyFromBuffer(frame_small_rgb)
        self.image_container.SetInactiveBitmap(self.bmp)
        #self.image_container.Refresh()
