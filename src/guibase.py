# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.10.0-4761b0c)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class Guibase
###########################################################################

class Guibase ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		fgSizer1 = wx.FlexGridSizer( 1, 2, 0, 0 )
		fgSizer1.SetFlexibleDirection( wx.BOTH )
		fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_bitmap1 = wx.StaticBitmap( self, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_bitmap1, 0, wx.ALL, 5 )

		bSizer1 = wx.BoxSizer( wx.VERTICAL )

		self.tgl_btn_start_camera = wx.ToggleButton( self, wx.ID_ANY, u"Start Camera", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.tgl_btn_start_camera, 0, wx.ALL|wx.EXPAND, 5 )

		self.tgl_btn_show_feed = wx.ToggleButton( self, wx.ID_ANY, u"Show Feed", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.tgl_btn_show_feed, 0, wx.ALL|wx.EXPAND, 5 )

		self.tgl_btn_touchcontrol = wx.ToggleButton( self, wx.ID_ANY, u"Enable TouchControl", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.tgl_btn_touchcontrol, 0, wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( bSizer1, 1, wx.EXPAND, 5 )


		self.SetSizer( fgSizer1 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.tgl_btn_start_camera.Bind( wx.EVT_TOGGLEBUTTON, self.on_tgl_camera )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def on_tgl_camera( self, event ):
		event.Skip()


