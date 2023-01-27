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

		self.image_container = wx.adv.AnimationCtrl( self, wx.ID_ANY, wx.adv.NullAnimation, wx.DefaultPosition, wx.Size( 900,500 ), wx.adv.AC_DEFAULT_STYLE )
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

		self.infogrid = wx.grid.Grid( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )

		# Grid
		self.infogrid.CreateGrid( 0, 2 )
		self.infogrid.EnableEditing( False )
		self.infogrid.EnableGridLines( True )
		self.infogrid.EnableDragGridSize( False )
		self.infogrid.SetMargins( 0, 0 )

		# Columns
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

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def on_close( self, event ):
		event.Skip()

	def on_tgl_camera( self, event ):
		event.Skip()


