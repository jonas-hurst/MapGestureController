# MapGestureController

Master's Thesis Project by Jonas Hurst: Tool to enable freehand gesture interaction with digital maps.
Uses Microsoft's **Azure Kinect** camera to track the person interacting with the map.

Supports: Pan, Zoom and Retrieve operations for maps on the web

To achieve panning, zooming and retrieving, this app simulates Touchscreen interactions.
For this reason, This program interfaces Windows' Winuser.h library (./src/touchcontrol/_wrapper.py). It is therefore **WINDOWS ONLY**.


https://github.com/jonas-hurst/MapGestureController/assets/76062450/ee1b6a6d-1fe2-47d1-a7d1-bdeda7c36a7b


## Starting the app
* Install Azure Kinect Sensor SDK
* Install Azure Kinect Body Tracking SDK
* Install python packages via `pip install -r requirements.txt`
* Connect Azure Kinect camera to your
* run ./src/app.py

## Using the app
* Define your screen environment in screen.py file (only supports multi-screen environments with screens next to each other, not on top of each other)
* In graphics card driver, join screens to one big screen (look for e.g. mosaic, nvidia surround, ...)
* Click "Start Camera" button" to start the camera
* (optional) Click "Show Feed" button do display camera feed in the UI
* Click "Enable TouchControl" button to give the program control over the touch screen
* Select either Pointer-to-Feature or Feature-to-Pointer Retrieve mechanism

## Visualization
* This tool is made to control maps on a web browser
* It is a lot easier if the enduser knows, what he is pointing at currently.
* Therefore, install [this](https://github.com/jonas-hurst/MGC_vis_extension) extension in your chrome browser to visualize your interactions (currently only supports OSM, GMAPS and locally hosted web pages)
* If using this plugin, start this program first, then go to website (e.g. openstreetmap.org)
* Browser will ask you if you want to connect to server > Click Okay
* A dot will appear at the location you are pointing at

## Gestures
* Panning: Point somewhere in the map with one hand, make a fist, move your hand, stop makingg a fist
* Zooming: Point at two locations in the map, Make two fists, move hands apart/together, open hands
* Retrieving: Two different mechanisms are implemented to enable this operation
    * Pointer-to-Feature: Point at the spatial feature you want to Retrieve from, move your hand in a swift motion towards the pointer. The spatial feature where the pointer is situated at will be retrieved from.
	* Feature-to-Pointer: Pan and Zoom the map so that the spatial feature to Retrieve from is in the screen's center, behind the cross-hairs. Move your hand in a swift motion towards the pointer. Whatever is behind the cross-hairs will be retrieved from.

## GUI
* Gui is created using wxPythong
* To modify GUI, open ./gui.fbtp file in wxFormBuilder (v. 3.10.0)
* In wxFormBuilder, select "File > Generate Code" to generate GUI base classes (./src/guibase.py)
* To manually modify GUI, use ./src/guibaseExtended.py, which inherits from ./src/guibase.py
* To give functionality to GUI, use ./src/gui.py, which inherits from ./src/guibaseExtended.py
