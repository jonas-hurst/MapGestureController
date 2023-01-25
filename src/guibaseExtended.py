from guibase import Guibase
import wx
import numpy as np
from cv2 import resize, cvtColor, COLOR_BGR2RGB


class GuibaseExtended(Guibase):
    """
    Class to extend Guibase.
    Guibase is automatically generated from wxFormBuilder.
    This class extends the GUI with GUI-Elements that are not supported by wxFormBuilder.
    gui.MainWindow inherits from GuibaseExtended to implement functionality.
    """

    def __init__(self, parent):
        Guibase.__init__(self, parent)

        self.img_panel = ImagePanel(self)


class ImagePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        width, height = 854, 480

        self.SetSize((width, height))

        frame = np.zeros((width, height, 3))
        self.bmp = wx.Bitmap.FromBuffer(width, height, frame)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def set_bitmap(self, frame: np.ndarray):
        frame_small = resize(frame.copy(), (854, 480))
        frame_small_rgb = cvtColor(frame_small, COLOR_BGR2RGB)
        self.bmp.CopyFromBuffer(frame_small_rgb)
        self.Refresh()

