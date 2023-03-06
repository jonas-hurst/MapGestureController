import wx

from guibaseExtended import GuibaseExtended, CalibrateDialogExtended
from interaction_controller import InteractionController, CameraException
from screen import *
from constants import *


class MainWindow(GuibaseExtended):
    def __init__(self, parent):
        GuibaseExtended.__init__(self, parent)

        self.infodata: dict = self.initialize_infodata()
        self.set_datagrid_values(self.infodata)

        self.interaction_controller = InteractionController(self, self.infodata)

    def on_tgl_camera(self, event):
        btn_value = self.tgl_btn_start_camera.Value
        try:
            if btn_value:
                self.interaction_controller.start_camera()
            else:
                self.interaction_controller.stop_camera()
            GuibaseExtended.on_tgl_camera(self, event)
        except CameraException as e:
            # show error message if zero or more than 1 camera are connecetd to pc
            wx.MessageDialog(self, str(e), style=wx.ICON_ERROR).ShowModal()

    def on_tgl_show(self, event):
        btn_value = self.tgl_btn_show_feed.Value
        self.interaction_controller.toggle_show_camerafeed(btn_value)

    def on_tgl_touchcontrol(self, event):
        self.interaction_controller.touch_control_enabled = self.tgl_btn_touchcontrol.Value

    def on_close(self, event):
        self.interaction_controller.stop_camera()
        GuibaseExtended.on_close(self, event)

    def on_interaction_mechanism_chagned(self, event):
        item = self.interaction_mechanism_choice.GetSelection()
        if item == 0:
            self.interaction_controller.interaction_mechanism = InteractionMechanism.SELECT_RIGHT_PAN_LEFT
        elif item == 1:
            self.interaction_controller.interaction_mechanism = InteractionMechanism.SELECT_LEFT_PAN_RIGHT
        elif item == 2:
            self.interaction_controller.interaction_mechanism = InteractionMechanism.SELECT_BOTH_PAN_BOTH

    def on_selection_mechanism_changed(self, event):
        item = self.selection_mechanism_choice.GetSelection()
        if item == 0:
            self.interaction_controller.pointing_mechanism = PointingMechanism.POINTER_TO_OBJECT
        elif item == 1:
            self.interaction_controller.pointing_mechanism = PointingMechanism.OBJECT_TO_POITNER

    def on_screen_changed(self, event):
        item = self.screen_choice.GetSelection()
        if item == 0:
            self.interaction_controller.set_screen_environment(SCREEN_SINGLE_ABOVE)
        elif item == 1:
            self.interaction_controller.set_screen_environment(SCREEN_SINGLE_BELOW)
        elif item == 2:
            self.interaction_controller.set_screen_environment(SCREENS_IVE)

    def on_calibrate(self, event):
        dlg = CalibrateDialogWindow(self,
                                    self.interaction_controller.get_1euro_tune_function(),
                                    self.interaction_controller.get_1euro_min_cutoff(),
                                    self.interaction_controller.get_1euro_beta_value())
        dlg.ShowModal()

    def initialize_infodata(self) -> dict:
        d = {"fps": 0,
             "bodies": "n.a.",
             "pitch": "n.a.",
             "roll": "n.a.",
             "left": HandState.UNTRACKED.name,
             "right": HandState.UNTRACKED.name,
             "operation": Operation.IDLE.name,
             "cut": 0,
             "beta": 0}
        return d


class CalibrateDialogWindow(CalibrateDialogExtended):
    def __init__(self, parent, tunefunction, cutoff, beta):
        CalibrateDialogExtended.__init__(self, parent)

        self.tuneunction = tunefunction

        self.slider_mincutoff.SetValue(int(cutoff * 100000))
        self.slider_beta.SetValue(int(beta * 100))

    def on_okay(self, event):
        self.Close()

    def on_slider_changed(self, event):
        beta_value = self.slider_beta.GetValue() / 1000
        mincutoff_value = self.slider_mincutoff.GetValue() / 100000
        self.tuneunction(min_cutoff=mincutoff_value, beta=beta_value)
