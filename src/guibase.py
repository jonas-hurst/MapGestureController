# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.10.0-4761b0c)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.adv
import wx.grid

###########################################################################
## Class Guibase
###########################################################################

class Guibase ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size( -1,-1 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		fgSizer1 = wx.FlexGridSizer( 1, 2, 0, 0 )
		fgSizer1.SetFlexibleDirection( wx.BOTH )
		fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.image_container = wx.adv.AnimationCtrl( self, wx.ID_ANY, wx.adv.NullAnimation, wx.DefaultPosition, wx.Size( 900,675 ), wx.adv.AC_DEFAULT_STYLE )
		fgSizer1.Add( self.image_container, 0, wx.ALL, 5 )

		bSizer1 = wx.BoxSizer( wx.VERTICAL )

		self.tgl_btn_start_camera = wx.ToggleButton( self, wx.ID_ANY, u"Start Camera", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.tgl_btn_start_camera, 0, wx.ALL|wx.EXPAND, 5 )

		self.tgl_btn_show_feed = wx.ToggleButton( self, wx.ID_ANY, u"Show Feed", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.tgl_btn_show_feed.Enable( False )

		bSizer1.Add( self.tgl_btn_show_feed, 0, wx.ALL|wx.EXPAND, 5 )

		self.tgl_btn_touchcontrol = wx.ToggleButton( self, wx.ID_ANY, u"Enable TouchControl", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.tgl_btn_touchcontrol.Enable( False )

		bSizer1.Add( self.tgl_btn_touchcontrol, 0, wx.ALL|wx.EXPAND, 5 )

		self.calibrate_button = wx.Button( self, wx.ID_ANY, u"Calibrate", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.calibrate_button.Enable( False )

		bSizer1.Add( self.calibrate_button, 0, wx.ALL|wx.EXPAND, 5 )

		interaction_mechanism_choiceChoices = [ u"Select: right, Pan: left", u"Select: left, Pan: right", u"Select: both, Pan: both" ]
		self.interaction_mechanism_choice = wx.Choice( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, interaction_mechanism_choiceChoices, 0 )
		self.interaction_mechanism_choice.SetSelection( 0 )
		bSizer1.Add( self.interaction_mechanism_choice, 0, wx.ALL|wx.EXPAND, 5 )

		selection_mechanism_choiceChoices = [ u"Pointer to Object", u"Object to Pointer" ]
		self.selection_mechanism_choice = wx.Choice( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, selection_mechanism_choiceChoices, 0 )
		self.selection_mechanism_choice.SetSelection( 0 )
		bSizer1.Add( self.selection_mechanism_choice, 0, wx.ALL|wx.EXPAND, 5 )

		screen_choiceChoices = [ u"single screen above", u"single screen below", u"IVE" ]
		self.screen_choice = wx.Choice( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, screen_choiceChoices, 0 )
		self.screen_choice.SetSelection( 0 )
		bSizer1.Add( self.screen_choice, 0, wx.ALL|wx.EXPAND, 5 )

		self.infogrid = wx.grid.Grid( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )

		# Grid
		self.infogrid.CreateGrid( 0, 2 )
		self.infogrid.EnableEditing( False )
		self.infogrid.EnableGridLines( True )
		self.infogrid.EnableDragGridSize( False )
		self.infogrid.SetMargins( 0, 0 )

		# Columns
		self.infogrid.SetColSize( 0, 70 )
		self.infogrid.SetColSize( 1, 130 )
		self.infogrid.EnableDragColMove( False )
		self.infogrid.EnableDragColSize( False )
		self.infogrid.SetColLabelValue( 0, u"key" )
		self.infogrid.SetColLabelValue( 1, u"value" )
		self.infogrid.SetColLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

		# Rows
		self.infogrid.AutoSizeRows()
		self.infogrid.EnableDragRowSize( False )
		self.infogrid.SetRowLabelSize( 0 )
		self.infogrid.SetRowLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

		# Label Appearance

		# Cell Defaults
		self.infogrid.SetDefaultCellAlignment( wx.ALIGN_LEFT, wx.ALIGN_TOP )
		bSizer1.Add( self.infogrid, 1, wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( bSizer1, 1, wx.EXPAND, 5 )


		self.SetSizer( fgSizer1 )
		self.Layout()
		fgSizer1.Fit( self )

		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_CLOSE, self.on_close )
		self.tgl_btn_start_camera.Bind( wx.EVT_TOGGLEBUTTON, self.on_tgl_camera )
		self.tgl_btn_show_feed.Bind( wx.EVT_TOGGLEBUTTON, self.on_tgl_show )
		self.tgl_btn_touchcontrol.Bind( wx.EVT_TOGGLEBUTTON, self.on_tgl_touchcontrol )
		self.calibrate_button.Bind( wx.EVT_BUTTON, self.on_calibrate )
		self.interaction_mechanism_choice.Bind( wx.EVT_CHOICE, self.on_interaction_mechanism_chagned )
		self.selection_mechanism_choice.Bind( wx.EVT_CHOICE, self.on_selection_mechanism_changed )
		self.screen_choice.Bind( wx.EVT_CHOICE, self.on_screen_changed )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def on_close( self, event ):
		event.Skip()

	def on_tgl_camera( self, event ):
		event.Skip()

	def on_tgl_show( self, event ):
		event.Skip()

	def on_tgl_touchcontrol( self, event ):
		event.Skip()

	def on_calibrate( self, event ):
		event.Skip()

	def on_interaction_mechanism_chagned( self, event ):
		event.Skip()

	def on_selection_mechanism_changed( self, event ):
		event.Skip()

	def on_screen_changed( self, event ):
		event.Skip()


###########################################################################
## Class CalibrateDialog
###########################################################################

class CalibrateDialog ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Calibrate Filter", pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		fgSizer2 = wx.FlexGridSizer( 4, 2, 0, 0 )
		fgSizer2.SetFlexibleDirection( wx.BOTH )
		fgSizer2.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.min_cutoff = wx.StaticText( self, wx.ID_ANY, u"Min Cutoff", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.min_cutoff.Wrap( -1 )

		fgSizer2.Add( self.min_cutoff, 0, wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 5 )

		self.slider_mincutoff = wx.Slider( self, wx.ID_ANY, 100000, 0, 100000, wx.DefaultPosition, wx.Size( 500,-1 ), wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS|wx.SL_VALUE_LABEL )
		fgSizer2.Add( self.slider_mincutoff, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )

		self.m_staticline1 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		fgSizer2.Add( self.m_staticline1, 0, wx.EXPAND |wx.ALL, 5 )

		self.m_staticline2 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		fgSizer2.Add( self.m_staticline2, 0, wx.EXPAND |wx.ALL, 5 )

		self.beta = wx.StaticText( self, wx.ID_ANY, u"Beta", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.beta.Wrap( -1 )

		fgSizer2.Add( self.beta, 0, wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 5 )

		self.slider_beta = wx.Slider( self, wx.ID_ANY, 0, 0, 100, wx.DefaultPosition, wx.Size( 500,-1 ), wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS|wx.SL_VALUE_LABEL )
		fgSizer2.Add( self.slider_beta, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )


		fgSizer2.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.ok = wx.Button( self, wx.ID_ANY, u"Okay", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.ok, 0, wx.ALL|wx.ALIGN_RIGHT, 5 )


		self.SetSizer( fgSizer2 )
		self.Layout()
		fgSizer2.Fit( self )

		self.Centre( wx.BOTH )

		# Connect Events
		self.slider_mincutoff.Bind( wx.EVT_SLIDER, self.on_slider_changed )
		self.slider_beta.Bind( wx.EVT_SLIDER, self.on_slider_changed )
		self.ok.Bind( wx.EVT_BUTTON, self.on_okay )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def on_slider_changed( self, event ):
		event.Skip()


	def on_okay( self, event ):
		event.Skip()


