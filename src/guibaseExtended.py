import wx
from cv2 import resize,cvtColor, COLOR_BGR2RGB
import numpy as np

from guibase import Guibase, CalibrateDialog, SettingsDialog


class GuibaseExtended(Guibase):
    """
    Class to extend Guibase (generated from wxFormBuilder) with custom GUI functionality.
    This class should contain all custom GUI code.
    This class can then be derived, where then interactino logic resides.
    """
    def __init__(self, parent):
        Guibase.__init__(self, parent)

        self.Bind(wx.EVT_SIZE, self.on_resize)

        self.image_width, self.image_height = 900, 675

        frame = np.zeros((self.image_width, self.image_height, 3))
        self.bmp = wx.Bitmap.FromBuffer(self.image_width, self.image_height, frame)
        self.image_container.SetInactiveBitmap(self.bmp)
        self.image_container.SetBackgroundStyle(wx.BG_STYLE_PAINT)

    def on_resize(self, event):
        pass

    def on_tgl_camera(self, event):
        btn_value = self.tgl_btn_start_camera.Value
        self.tgl_btn_show_feed.Enable(btn_value)
        self.tgl_btn_touchcontrol.Enable(btn_value)
        self.calibrate_button.Enable(btn_value)
        self.settings_button.Enable(not btn_value)
        if btn_value:
            self.tgl_btn_start_camera.SetLabelText("Stop Camera")
        else:
            self.tgl_btn_start_camera.SetLabelText("Start Camera")

    def on_close(self, event):
        Guibase.on_close(self, event)

    def set_datagrid_values(self, tabledata: dict):
        """
        Populates the datagrid with Key-Value pairs
        :param tabledata: Data to be displayed in Datagrid. Must be dict.
        :return: None
        """
        if self.infogrid.NumberRows != len(tabledata):
            self.infogrid.AppendRows(len(tabledata), False)

        rowcount = 0
        for idx, key in enumerate(tabledata):
            self.infogrid.SetCellValue(idx, 0, key)
            self.infogrid.SetCellValue(idx, 1, str(tabledata[key]))
            rowcount += 1

    def set_bitmap(self, frame):
        """
        Method to set the image on screen.
        :param frame: 2D numpy array containing the image
        :return: None
        """
        frame_small_rgb = resize(frame.copy(), (self.image_width, self.image_height))
        self.bmp.CopyFromBuffer(frame_small_rgb)
        self.image_container.SetInactiveBitmap(self.bmp)


class CalibrateDialogExtended(CalibrateDialog):
    def __init__(self, parent):
        CalibrateDialog.__init__(self, parent)


class SettingsDialogExtended(SettingsDialog):
    def __init__(self, parent):
        SettingsDialog.__init__(self, parent)
