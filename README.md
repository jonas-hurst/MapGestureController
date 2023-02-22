# MapGestureController

Master's Thesis Project of Jonas Hurst: Tool to control a large screen map environment remotely, using an **Azure Kinect** camera.

Supports: Panning, Zooming and Selecting for maps on the web

To achieve panning, zooming and selecting, this app simulates Touchscreen interactions.
This is achieved interfacing Winuser.h library (./src/touchcontrol/_wrapper.py) and is therefore **WINDOWS ONLY**

## Starting the app
* Install Azure Kinect Sensor SDK
* Install Azure Kinect Body Tracking SDK
* Install python packages via ...
* Install pyKinectAzure (use my fork from ..., not what is on pypi)
* Adjust camera and body tracking configuratino to fit your needs (./src/cameracontrol.py, TrackerController.startCamera() and TrackerControlelr.startTracker())
* Connect Azure Kinect camera to your
* run ./src/app.py

## Using the app
* Define your screen environment in screen.py file (only supports multi-screen environments with screens next to each other, not on top of each other)
* In graphics card driver, join screens to one big screen (e.g. mosaic, nvidia surround, ...)
* Click "Start Camera" button" to start the camera
* (optional) Click "Show Feed" button do display camera feed
* Click "Enable TouchControl" button to give the program control over the touch screen

## Visualization
* This tool is made to control maps on a web browser
* It is a lot easier if the enduser knows, what he is pointing at currently.
* Therefore, install this extension in your chrome browser to help you visualize (currently only supports OSM and GMAPS)
* If using this plugin, start this program first, then go to website (e.g. openstreetmap.org)
* Browser will ask you if you want to connect to server > Click Okay
* A dot will appear at the location you are pointing at

## Gestures
* Panning: Point at something, make a fist, move your hand, stop makingg a fist
* Zooming: Point at two things, Make two fists, move hands apart/together, open hands
* Selecting: TODO

## GUI
* Gui is created using wxPythong
* To modify GUI, open ./gui.fbtp file in wxFormBuilder (v. 3.10.0)
* In wxFormBuilder, select "File > Generate Code" to generate GUI base classes (./src/guibase.py)
* To manually modify GUI, use ./src/guibaseExtended.py, which inherits from ./src/guibase.py
* To give functionality to GUI, use ./src/gui.py, which inherits from ./src/guibaseExtended.py
