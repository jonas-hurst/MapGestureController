from ctypes import *
from ctypes.wintypes import *

from time import sleep

# Constants

# For touchMask
TOUCH_MASK_NONE = 0x00000000  # Default
TOUCH_MASK_CONTACTAREA = 0x00000001
TOUCH_MASK_ORIENTATION = 0x00000002
TOUCH_MASK_PRESSURE = 0x00000004
TOUCH_MASK_ALL = 0x00000007

# For touchFlag
TOUCH_FLAG_NONE = 0x00000000

# For pointerType
PT_POINTER = 0x00000001  # All
PT_TOUCH = 0x00000002
PT_PEN = 0x00000003
PT_MOUSE = 0x00000004

# For pointerFlags
POINTER_FLAG_NONE = 0x00000000  # Default
POINTER_FLAG_NEW = 0x00000001
POINTER_FLAG_INRANGE = 0x00000002
POINTER_FLAG_INCONTACT = 0x00000004
POINTER_FLAG_FIRSTBUTTON = 0x00000010
POINTER_FLAG_SECONDBUTTON = 0x00000020
POINTER_FLAG_THIRDBUTTON = 0x00000040
POINTER_FLAG_FOURTHBUTTON = 0x00000080
POINTER_FLAG_FIFTHBUTTON = 0x00000100
POINTER_FLAG_PRIMARY = 0x00002000
POINTER_FLAG_CONFIDENCE = 0x00004000
POINTER_FLAG_CANCELED = 0x00008000
POINTER_FLAG_DOWN = 0x00010000
POINTER_FLAG_UPDATE = 0x00020000
POINTER_FLAG_UP = 0x00040000
POINTER_FLAG_WHEEL = 0x00080000
POINTER_FLAG_HWHEEL = 0x00100000
POINTER_FLAG_CAPTURECHANGED = 0x00200000


class POINTER_INFO(Structure):
    _fields_=[("pointerType",c_uint32),
              ("pointerId",c_uint32),
              ("frameId",c_uint32),
              ("pointerFlags",c_int),
              ("sourceDevice",HANDLE),
              ("hwndTarget",HWND),
              ("ptPixelLocation",POINT),
              ("ptHimetricLocation",POINT),
              ("ptPixelLocationRaw",POINT),
              ("ptHimetricLocationRaw",POINT),
              ("dwTime",DWORD),
              ("historyCount",c_uint32),
              ("inputData",c_int32),
              ("dwKeyStates",DWORD),
              ("PerformanceCount",c_uint64),
              ("ButtonChangeType",c_int)
              ]

class POINTER_TOUCH_INFO(Structure):
    _fields_=[("pointerInfo",POINTER_INFO),
              ("touchFlags",c_int),
              ("touchMask",c_int),
              ("rcContact", RECT),
              ("rcContactRaw",RECT),
              ("orientation", c_uint32),
              ("pressure", c_uint32)]


ntouch = 2

touchInfo = (POINTER_TOUCH_INFO * ntouch)()

touchInfo[0].pointerInfo.pointerType = PT_TOUCH
touchInfo[0].pointerInfo.pointerId = 0
touchInfo[0].pointerInfo.ptPixelLocation.y = 1000
touchInfo[0].pointerInfo.ptPixelLocation.x = 500

touchInfo[0].touchFlags = TOUCH_FLAG_NONE
touchInfo[0].touchMask = TOUCH_MASK_ALL
touchInfo[0].orientation = 90
touchInfo[0].pressure = 32000
touchInfo[0].rcContact.top = touchInfo[0].pointerInfo.ptPixelLocation.y - 2
touchInfo[0].rcContact.bottom = touchInfo[0].pointerInfo.ptPixelLocation.y + 2
touchInfo[0].rcContact.left = touchInfo[0].pointerInfo.ptPixelLocation.x - 2
touchInfo[0].rcContact.right = touchInfo[0].pointerInfo.ptPixelLocation.x + 2

touchInfo[1].pointerInfo.pointerType = PT_TOUCH
touchInfo[1].pointerInfo.pointerId = 1
touchInfo[1].pointerInfo.ptPixelLocation.y = 900
touchInfo[1].pointerInfo.ptPixelLocation.x = 300

touchInfo[1].touchFlags = TOUCH_FLAG_NONE
touchInfo[1].touchMask = TOUCH_MASK_ALL
touchInfo[1].orientation = 90
touchInfo[1].pressure = 32000
touchInfo[1].rcContact.top = touchInfo[1].pointerInfo.ptPixelLocation.y - 2
touchInfo[1].rcContact.bottom = touchInfo[1].pointerInfo.ptPixelLocation.y + 2
touchInfo[1].rcContact.left = touchInfo[1].pointerInfo.ptPixelLocation.x - 2
touchInfo[1].rcContact.right = touchInfo[1].pointerInfo.ptPixelLocation.x + 2

if windll.user32.InitializeTouchInjection(ntouch, 2) is False:
    print("Initialized Touch Injection Error")
else:
    print("initilaization successful")


def _inject_single(idx: int = 0):
    """
    Method to inject a single touch pointer into the system.
    Injected pointer is touchInfo[0]
    :param idx: Index which pointer in touchInfo should be injected, defaults to 0
    :return: None
    """
    if windll.user32.InjectTouchInput(1, byref(touchInfo[idx])) is False:
        raise Exception("Touch Injection went wrong")


def _inject_double():
    """
    Method to inject a double touch pointer into the systsem.
    Injected pointers are tuochInfo
    :return: None
    """
    if windll.user32.InjectTouchInput(ntouch, byref(touchInfo)) is False:
        raise Exception("Touch Injection went wrong")


def _pointer_make_contact_single(idx=0):
    """
    Update pointer flags to indicate that a pointer has made contact with the screen.
    Simulates a finger touching the screen
    :param idx: Index which pointer in touchInfo should simulate contact, defaults to 0
    :return: None
    """
    touchInfo[idx].pointerInfo.pointerFlags = (POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT)


def _pointer_make_contact_double():
    """
    Update poitner flags to indicate they have made contact with the screen.
    Simulates multiple fingers touching the screen
    :return:
    """
    for idx in range(len(touchInfo)):
        _pointer_make_contact_single(idx)


def _pointer_update_single(idx: int = 0):
    """
    Update pointer flags to indcate a pointer has changed psoition on screen.
    Simulates a finger moving on screen.
    :param idx: Index which pointer in touchInfo should update, defaults to 0
    :return: None
    """
    touchInfo[idx].pointerInfo.pointerFlags = (POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_UPDATE)


def _pointer_update_double():
    """
    Update pointer flags to indicate their position has chagned on screen.
    :return:
    """
    for idx in range(len(touchInfo)):
        _pointer_update_single(idx)


def _pointer_leave_single(idx: int = 0):
    """
    Update pointer flags to indicate a pointer has left the screen.
    Simulates a finger taken off the touch screen
    :param idx: Index which pointer in touchInfo should leave, defaults to 0
    :return: None
    """
    touchInfo[idx].pointerInfo.pointerFlags = POINTER_FLAG_UP


def _pointer_leave_double():
    """
    Update pointer flags to indicate they have left the screen.
    :return: None
    """
    for idx in range(len(touchInfo)):
        _pointer_leave_single(idx)


def makeTap(x, y):
    touchInfo[0].pointerInfo.ptPixelLocation.y = y
    touchInfo[0].pointerInfo.ptPixelLocation.x = x

    # Press Down
    _pointer_make_contact_single()
    _inject_single()

    # Pull Up
    _pointer_leave_single()
    _inject_single()


def makeSwipe(x_start, y_start, x_end, y_end, num_steps=10):
    """
    Method to simulate a swiping motion on touch screen.
    Simulates one finger dragging over the touch screen.
    Example: Panning a map.
    :param x_start: x-coordinate of swiping start position
    :param y_start: y-coordinaet of swiping start position
    :param x_end: x-coordinate of swiping end position
    :param y_end: y-coordinate of swiping end position
    :param num_steps: Number of steps used for linear interpolation between start and end. Use higher number for smoother movement.
    :return: None
    """
    touchInfo[0].pointerInfo.ptPixelLocation.x = x_start
    touchInfo[0].pointerInfo.ptPixelLocation.y = y_start

    _pointer_make_contact_single()
    _inject_single()

    # Move toucher
    _pointer_update_single()

    x_step = int((x_end - x_start) / num_steps)
    y_step = int((y_end - x_end) / num_steps)
    for i in range(num_steps):
        touchInfo[0].pointerInfo.ptPixelLocation.x += x_step
        touchInfo[0].pointerInfo.ptPixelLocation.y += y_step

        _inject_single()

        sleep(0.01)

    # Pull Up
    _pointer_leave_single()

    _inject_single()


def makeZoom(x1_start, y1_start, x1_end, y1_end,
             x2_start, y2_start, x2_end, y2_end, num_steps=10):
    """
    Method simulating spreading multitouch gesture.
    Simulates two fingers dragging over the touch screen.
    Example: Two fingers performing an opening or closing gesture to zoom in/out of the map.
    :param x1_start: Starting Position X-Coord of Finger 1
    :param y1_start: Starting Position Y-Coord of Finger 1
    :param x1_end: Ending Position X-Coord of Finger 1
    :param y1_end: Ending Position Y-Coord of Finger 1
    :param x2_start: Starting Position X-Coord of Finger 2
    :param y2_start: Starting Position Y-Coord of Finger 2
    :param x2_end: Ending Position X-Coord of Finger 2
    :param y2_end: Ending Position Y-Coord of Finger 2
    :param num_steps: Number of steps used for linear interpolation between start and end. Use higher number for smoother movement.
    :return: None
    """
    touchInfo[0].pointerInfo.ptPixelLocation.x = x1_start
    touchInfo[0].pointerInfo.ptPixelLocation.y = y1_start

    touchInfo[1].pointerInfo.ptPixelLocation.x = x2_start
    touchInfo[1].pointerInfo.ptPixelLocation.y = y2_start

    # Press Down
    _pointer_make_contact_double()
    _inject_double()

    # Touch Move Simulate
    _pointer_update_double()

    x1_step = int((x1_end - x1_start) / num_steps)
    y1_step = int((y1_end - y1_start) / num_steps)
    x2_step = int((x2_end - x2_start) / num_steps)
    y2_step = int((y2_end - y2_start) / num_steps)
    for i in range(100):
        touchInfo[0].pointerInfo.ptPixelLocation.x += x1_step
        touchInfo[0].pointerInfo.ptPixelLocation.y += y1_step
        touchInfo[1].pointerInfo.ptPixelLocation.x += x2_step
        touchInfo[1].pointerInfo.ptPixelLocation.y += y2_step

        _inject_double()

        sleep(0.01)

    # Pull Up
    _pointer_leave_double()
    _inject_double()


# Examples:
# if __name__ == "__main__":
#     makeTap(1400, 400)
#     makeSwipe(1000, 600, 1800, 700, 100)
#     makeZoom(1500, 600, 1800, 400, 1400, 700, 1100, 900, num_steps=100)
