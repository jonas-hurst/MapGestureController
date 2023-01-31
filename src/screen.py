from geom import *
from numbers import Real


class Screen(Plane3D):
    def __init__(self, a: Real, b: Real, c: Real, d: Real, px_width: int, px_height: int, mm_width: int, mm_height: int):
        # TODO: Hard-code Sceren constraints (e.g. is always an upright plain)
        # TODO: Implement screen starting point (lower left corner?)

        Plane3D.__init__(self, a, b, c, d)

        self.px_width = px_width
        self.px_height = px_height

        self.mm_width = mm_width
        self.mm_height = mm_height

    def contains_point(self, pnt: Point3D, epsilon: float = 0.0001) -> bool:
        if not Plane3D.contains_point(self, pnt, epsilon):
            return False
        #TODO: Check if point is on screen

    def draw_point(self):
        #TODO: Draw intersection point on screen
        pass


if __name__ == "__main__":
    s = Screen(1, 0, 0, 0,
               9, 9, 9, 9)
    p = Point3D(0, 4.4476342224576, 2.97638583897)
    print(s.contains_point(p))
