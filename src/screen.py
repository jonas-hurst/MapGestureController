from geom import *
from numbers import Real


class Screen:
    def __init__(self, screen_id: int, lower_left_corner: Point3D, upper_right_corner: Point3D, px_width: int, px_height: int):
        """
        Initializes a new Screen object (e.g. TV screen or projection screen)
        :param lower_left_corner: Lower left corner of the screen (in Azure Kinect Depth camera coordinates)
        :param upper_right_corner: Upper right corner of the screen (in Azure Kinect Depth camera coordinates)
        :param px_width: Width of screen in pixels
        :param px_height: Height of screen in pixels
        """

        self.screen_id: int = screen_id

        self.__lower_left_corner: Point3D = lower_left_corner

        self.screen_plain = Plane3D.from_vectors(self.__lower_left_corner.get_pointvector(),
                                                 Vector3D.from_points(lower_left_corner, upper_right_corner),
                                                 Vector3D(0, -1, 0)   # Third vector just points upwards
                                                 )

        self.__min_x = min((lower_left_corner.x, upper_right_corner.x))
        self.__max_x = max((lower_left_corner.x, upper_right_corner.x))
        self.__min_y = min((lower_left_corner.y, upper_right_corner.y))
        self.__max_y = max((lower_left_corner.y, upper_right_corner.y))
        self.__min_z = min((lower_left_corner.z, upper_right_corner.z))
        self.__max_z = max((lower_left_corner.z, upper_right_corner.z))

        helper_vector = Vector3D.from_points(lower_left_corner, upper_right_corner)
        self.screen_width = Vector3D(helper_vector.x_dir, 0, helper_vector.z_dir).get_magnitude()
        self.screen_height = abs(upper_right_corner.y - lower_left_corner.y)

        self.px_width = px_width
        self.px_height = px_height

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

        point_vector = Vector3D.from_points(self.__lower_left_corner, point)
        height_px = point_vector.y_dir * (self.px_height / self.screen_height)
        width_px = Vector3D(point_vector.x_dir, 0, point_vector.z_dir).get_magnitude() * (self.px_width / self.screen_width)
        return int(width_px), int(height_px)


# Different Screen setup templates: Single Screen and 3-Display-Multiscreen. Set your screen in self.screens
# Screen coordinates with respect to Azure Kinect depth coordinate system

# Single Screen setup: One Screen underneath the Camera
SCREEN_SINGLE_BELOW: tuple[Screen] = (Screen(3,
                                             Point3D(-1100, 0, 0),
                                             Point3D(1100, 1280, 0),
                                             1920, 1200),)


# Single Screen setup: One screen above the camera
# Small Z offset of -1 to prevent rounding issues
SCREEN_SINGLE_ABOVE: tuple[Screen] = (Screen(3,
                                             Point3D(-1100, -1380, -1),
                                             Point3D( 1100,  -100, 0),
                                             1920, 1200),)


# Multi-Screen Setup: IVE Screens
# Small Z offset in screen 1 (z=-1) to prevent rounding issues
SCREENS_IVE: tuple[Screen, Screen, Screen] = (
    # left screen
    Screen(0,
           Point3D(1100, -1640, 0),
           Point3D(1209,  -360, 1890),
           1920, 1080),

    # middle screen
    Screen(1,
           Point3D(-1100, -1640, -1),  # z=-1 to prevent rounding issues when checking for point within bbox
           Point3D( 1100,  -360, 0),
           1920, 1080),

    # right screen
    Screen(2,
           Point3D(-1209, -1640, 1890),  # z=-1 to be consistent with middle screen
           Point3D(-1100,  -360,   -1),
           1920, 1080)
)


SCREEN_IVE_SIMPLE: tuple[Screen] = (
    Screen(4,
           Point3D(-3300, -1300, -1),
           Point3D( 3300,  -360,  0),
           5760, 1080),
)

