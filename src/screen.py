from geom import *
from numbers import Real


class Screen:
    def __init__(self, lower_left_corner: Point3D, upper_right_corner: Point3D, px_width: int, px_height: int):

        # Check if lower and upper corner are actually lower and upper left/right
        if (lower_left_corner.x > upper_right_corner.x or
                lower_left_corner.y > upper_right_corner.y or
                lower_left_corner.z > upper_right_corner.z):
            raise ValueError("Lower and upper corner values are not actually lower and upper corner")

        self.lower_left_corner: Point3D = lower_left_corner
        self.upper_right_corner: Point3D = upper_right_corner

        self.screen_plain = Plane3D.from_vectors(self.lower_left_corner.get_pointvector(),
                                                 Vector3D.from_points(lower_left_corner, upper_right_corner),
                                                 Vector3D(0, -1, 0)   # Third vector just points upwards
                                                 )

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

        if not self.lower_left_corner.x <= point.x <= self.upper_right_corner.x:
            print("check1 False")
            return False

        if not self.lower_left_corner.y <= point.y <= self.upper_right_corner.y:
            print("check2 False")
            return False

        if not self.lower_left_corner.z <= point.z <= self.upper_right_corner.z:
            print("check3 False")
            return False

        return True

    def draw_point(self):
        #TODO: Draw intersection point on screen
        pass


if __name__ == "__main__":
    s = Screen(1, 0, 0, 0,
               9, 9, 9, 9)
    p = Point3D(0, 4.4476342224576, 2.97638583897)
    print(s.contains_point(p))
