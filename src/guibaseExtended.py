import wx
from cv2 import resize,cvtColor, COLOR_BGR2RGB
import numpy as np

from guibase import Guibase


class GuibaseExtended(Guibase):
    def __init__(self, parent):
        Guibase.__init__(self, parent)

        width, height = 854, 480
        frame = np.zeros((width, height, 3))
        self.bmp = wx.Bitmap.FromBuffer(width, height, frame)
        self.image_container.SetInactiveBitmap(self.bmp)
        self.image_container.SetBackgroundStyle(wx.BG_STYLE_PAINT)

    def on_tgl_camera(self, event):
        btn_value = self.tgl_btn_start_camera.Value
        self.tgl_btn_show_feed.Enable(btn_value)
        self.tgl_btn_touchcontrol.Enable(btn_value)
        if btn_value:
            self.tgl_btn_start_camera.SetLabelText("Stop Camera")
        else:
            self.tgl_btn_start_camera.SetLabelText("Start Camera")

    def on_close(self, event):
        wx.Exit()

    def set_datagrid_values(self, tabledata: dict):
        if self.infogrid.NumberRows != len(tabledata):
            self.infogrid.AppendRows(len(tabledata), False)

        rowcount = 0
        for idx, key in enumerate(tabledata):
            self.infogrid.SetCellValue(idx, 0, key)
            self.infogrid.SetCellValue(idx, 1, str(tabledata[key]))
            rowcount += 1

    def set_bitmap(self, frame):
        frame_small = resize(frame.copy(), (854, 480))
        frame_small_rgb = cvtColor(frame_small, COLOR_BGR2RGB)
        self.bmp.CopyFromBuffer(frame_small_rgb)
        self.image_container.SetInactiveBitmap(self.bmp)
