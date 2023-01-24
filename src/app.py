import wx
from gui import MainWindow


def main():
    app = wx.App()
    gui = MainWindow(None)
    gui.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
