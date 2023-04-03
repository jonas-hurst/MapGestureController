from geom import *
from numbers import Real


class Screen:
    def __init__(self, screen_id: int, upper_left_corner: Point3D, lower_right_corner: Point3D, anchor: Point3D,
                 px_width: int, px_height: int):
        """
        Initializes a new Screen object (e.g. TV screen or projection screen)
        :param upper_left_corner: Upper left corner of the screen (in Azure Kinect Depth camera coordinates)
        :param lower_right_corner: Lower right corner of the screen (in Azure Kinect Depth camera coordinates)
        :param anchor: Anchor point, relative to which a screen is moved
        :param px_width: Width of screen in pixels
        :param px_height: Height of screen in pixels
        """

        self.screen_id: int = screen_id

        self.__anchor = anchor

        self.__upper_left_corner: Point3D = upper_left_corner
        self.__lower_right_corner: Point3D = lower_right_corner

        self.screen_plain: Plane3D = self.calc_screen_plain()

        self.__min_x: Real = 0
        self.__max_x: Real = 0
        self.__min_y: Real = 0
        self.__max_y: Real = 0
        self.__min_z: Real = 0
        self.__max_z: Real = 0
        self.calc_min_max_values()

        helper_vector = Vector3D.from_points(upper_left_corner, lower_right_corner)
        self.screen_width = Vector3D(helper_vector.x_dir, 0, helper_vector.z_dir).get_magnitude()
        self.screen_height = abs(upper_left_corner.y - lower_right_corner.y)

        self.px_width = px_width
        self.px_height = px_height

    def calc_screen_plain(self) -> Plane3D:
        p = Plane3D.from_vectors(self.__upper_left_corner.get_pointvector(),
                                 Vector3D.from_points(self.__upper_left_corner, self.__lower_right_corner),
                                 Vector3D(0, -1, 0)  # Third vector just points upwards
                                )
        return p

    def calc_min_max_values(self):
        self.__min_x = min((self.__upper_left_corner.x, self.__lower_right_corner.x))
        self.__max_x = max((self.__upper_left_corner.x, self.__lower_right_corner.x))
        self.__min_y = min((self.__upper_left_corner.y, self.__lower_right_corner.y))
        self.__max_y = max((self.__upper_left_corner.y, self.__lower_right_corner.y))
        self.__min_z = min((self.__upper_left_corner.z, self.__lower_right_corner.z))
        self.__max_z = max((self.__upper_left_corner.z, self.__lower_right_corner.z))

    def move_realtive_z(self, new_anchor_z: Real):

        z_diff_anchor_upperleft = self.__upper_left_corner.z - self.__anchor.z
        z_diff_anchor_lowerright = self.__lower_right_corner.z - self.__anchor.z

        self.__anchor.z = new_anchor_z

        self.__upper_left_corner.z = new_anchor_z + z_diff_anchor_upperleft
        self.__lower_right_corner.z = new_anchor_z + z_diff_anchor_lowerright
        self.screen_plain = self.calc_screen_plain()

        self.calc_min_max_values()

    def contains_point(self, point: Point3D) -> bool:
        """
        Checks if a Point is on the screen or not.
        :param point: The point to check
        :return: bool value indicating if point is on screen
        """

        # Check if point is contained within the screen plain
        if not self.screen_plain.contains_point(point, epsilon=0.0001):
            return False

        # Check if point is within the screen's bounding box
        if not self.check_point_in_screen_bbox(point):
            return False

        return True

    def check_point_in_screen_bbox(self, point: Point3D) -> bool:
        """
        Checks if point is located within the screens bbox.
        Bbox is defined by self.lower_left_corner and self.upper_right_corner in 3D space
        :param point: Point to be checked
        :return: Bool value indicating if point is within bbox
        """

        if not self.__min_x <= point.x <= self.__max_x:
            return False

        if not self.__min_y <= point.y <= self.__max_y:
            return False

        if not self.__min_z <= point.z <= self.__max_z:
            return False

        return True

    def coords_to_px(self, point: Point3D) -> (int, int):
        """
        Method to convert a point on screen to its pixel value. Error if Point is not on screen.
        :param point: The point to convert to pixel values
        :return: Pixel values for point. Length 2 tuple, two ints. First value is x, second one is y
        """

        # Check if point is on screen
        if not self.contains_point(point):
            raise ValueError("Point not on screen")

        point_vector = Vector3D.from_points(self.__upper_left_corner, point)
        height_px = point_vector.y_dir * (self.px_height / self.screen_height)
        width_px = Vector3D(point_vector.x_dir, 0, point_vector.z_dir).get_magnitude() * (self.px_width / self.screen_width)
        return int(width_px), int(height_px)


# Different Screen setup templates: Single Screen and 3-Display-Multiscreen. Set your screen in self.screens
# Screen coordinates with respect to Azure Kinect depth coordinate system


# Single Screen setup: One screen above the camera
# Small Z offset of -1 to prevent rounding issues
SCREEN_SINGLE_ABOVE_1200p: tuple[Screen] = (Screen(3,
                                                   Point3D( 1100, -1380, -1),
                                                   Point3D(-1100,  -100,  0),
                                                   Point3D(0, 0, 0),
                                                   1920, 1200),)


SCREEN_SINGLE_ABOVE_FHD: tuple[Screen] = (Screen(3,
                                                 Point3D( 1100, -1380, -1),
                                                 Point3D(-1100,  -100,  0),
                                                 Point3D(0, 0, 0),
                                                 1920, 1080),)


# Single UHD Screen setup: One screen above the camera
# Small Z offset of -1 to prevent rounding issues
SCREEN_SINGLE_ABOVE_UHD: tuple[Screen] = (Screen(3,
                                                  Point3D( 1100, -1380, -1),
                                                  Point3D(-1100,  -100,  0),
                                                  Point3D(0, 0, 0),
                                                  3840, 2160),)


# Multi-Screen Setup: IVE Screens
# Small Z offset in screen 1 (z=-1) to prevent rounding issues
SCREENS_IVE: tuple[Screen, Screen, Screen] = (
    # left screen
    Screen(0,
           Point3D(1290, -1640, 1890),
           Point3D(1100,  -360,    0),
           Point3D(0, 0, 0),
           1920, 1080),

    # middle screen
    Screen(1,
           Point3D( 1100, -1640, -1),  # z=-1 to prevent rounding issues when checking for point within bbox
           Point3D(-1100,  -360,  0),
           Point3D(0, 0, 0),
           1920, 1080),

    # right screen
    Screen(2,
           Point3D(-1100, -1640,   -1),  # z=-1 to be consistent with middle screen
           Point3D(-1209,  -360, 1890),
           Point3D(0, 0, 0),
           1920, 1080)
)


SCREEN_IVE_SIMPLE: tuple[Screen] = (
    Screen(4,
           Point3D( 3300, -1300, -1),
           Point3D(-3300,  -360,  0),
           Point3D(0, 0, 0),
           5760, 1080),
)

