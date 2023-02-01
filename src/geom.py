"""
A module for handling geometries in 3D space
"""
from __future__ import annotations
from numbers import Real
import numpy as np


class ParallelError(Exception):
    """
    Exception to be raised if a geometric operation cannot be executed due to parallel vectors.
    """
    pass


class Point3D:
    """
    Represents a point in 3D space
    """
    def __init__(self, x: Real, y: Real, z: Real):
        """
        Constructs a point in 3D space from xyz coordinates
        :param x: X-Coordinaet of point
        :param y: Y-coordinate of point
        :param z: Z-coordinate of point
        """
        self.coords: np.array = np.array([x, y, z])
        self.x = self.coords[0]
        self.y = self.coords[1]
        self.z = self.coords[2]

    def __str__(self):
        return "Point3D: " + self.coords.__str__()

    def get_pointvector(self) -> Vector3D:
        """
        Transforms the point to its positional vector:
        Vector from (0,0,0) to point.
        :return: Positional vector
        """
        return Vector3D(self.coords[0], self.coords[1], self.coords[2])

    def distance(self, point: Point3D) -> float:
        """
        Calculates the euclidian distance between self and point
        :param point: the other point to calculate the distance
        :return: the distance
        """
        return np.linalg.norm(self.coords - point.coords)


class Vector3D:
    """
    Represents a vector in 3D space
    """
    def __init__(self, x_dir: Real, y_dir: Real, z_dir: Real):
        self.coords: np.array = np.array([x_dir, y_dir, z_dir])
        self.x_dir = self.coords[0]
        self.y_dir = self.coords[1]
        self.z_dir = self.coords[2]

    def __sub__(self, other: Vector3D) -> Vector3D:
        """
        Calculates the difference between vectors self and other
        :param other: the other vector
        :return: Vector-Difference
        """
        diff = self.coords - other.coords
        return Vector3D(diff[0], diff[1], diff[2])

    def __str__(self):
        return "Vector3D: " + self.coords.__str__()

    def get_magnitude(self) -> float:
        """
        Calculates the magnitude of the vector, using euclidian norm
        :return: The magnitude
        """
        return np.linalg.norm(self.coords)

    @staticmethod
    def check_parallel(v1: Vector3D, v2: Vector3D, epsilon: float = 0.0001) -> bool:
        """
        Method to check if two vectors are parllel (or anti-parallel)
        :param v1: The first vector
        :param v2: The second vector
        :param epsilon: epsilon value to account for float rounding errors
        :return: bool value indicating if vectors are parallel
        """

        value = abs(np.dot(v1.coords, v2.coords) / (np.linalg.norm(v1.coords)*np.linalg.norm(v2.coords)))
        return value > 1-epsilon

    @staticmethod
    def check_orthogonal(v1: Vector3D, v2: Vector3D, epsilon: float = 0.0001) -> bool:
        """
        Method to check if two vectors are orthogonal
        :param v1: The first vector
        :param v2: The second vector
        :param epsilon: episilon value to account for float rounding numbers
        :return: bool value indicating if vectors are orthogonal
        """

        value = abs(np.dot(v1.coords, v2.coords) / (np.linalg.norm(v1.coords) * np.linalg.norm(v2.coords)))
        return value < epsilon

    @staticmethod
    def from_points(point1: Point3D, point2: Point3D) -> Vector3D:
        """
        Calculates the vector between two points
        :param point1: The first point
        :param point2: The second point
        :return: The vector
        """
        return point2.get_pointvector() - point1.get_pointvector()


class Line:
    """
    Represents a line in 3D space
    """
    def __init__(self, support_vector: Vector3D, dir_vector: Vector3D):
        """
        Constructor to create a line in 3D space
        :param support_vector: Vector from (0,0,0) to a point on the line
        :param dir_vector: Vector from support-vector point to an arbitrary second point on line
        """
        self.support_vector: Vector3D = support_vector
        self.directional_vector: Vector3D = dir_vector

    def __str__(self):
        return f"Line:\n" \
               f"\tSupporting Vector: {self.support_vector.__str__()}\n" \
               f"\tDirectional Vector: {self.directional_vector.__str__()}"

    @staticmethod
    def from_points(point1: Point3D, point2: Point3D) -> Line:
        """
        Creates a line intersecting two poitns
        :param point1: First point on the line
        :param point2: Second point on the line
        :return: The line intersecting the points
        """
        supp = point1.get_pointvector()
        direc = Vector3D.from_points(point1, point2)
        return Line(supp, direc)


class Plane3D:
    """
    Class to represent a plane in 3D-space
    """

    def __init__(self, a: Real, b: Real, c: Real, d: Real):
        """
        Initializes a Plane of type: a*x1 b b*x2 + c*x3 = d
        :param a: Parameter a
        :param b: Parameter b
        :param c: Parameter c
        :param d: Parameter d
        """
        self.a, self.b, self.c, self.d = a, b, c, d

    def __str__(self) -> str:
        return "Plane:\n" \
               f"{self.a} * x1 + {self.b} * x2 + {self.c} * x3 = {self.d}"

    def contains_point(self, pnt: Point3D, epsilon: float = 0.0001) -> bool:
        """
        Method to check if a point pnt is part of the plane
        :param pnt: The point
        :param epsilon: epsilon value to account for float rounding errors
        :return: bool value indicating if point is part of the plane
        """
        test_val = self.a*pnt.x + self.b*pnt.y + self.c*pnt.z
        return abs(test_val - self.d) < epsilon

    def intersect_line(self, line: Line) -> Point3D:
        """
        Method to intersect the plane with a line
        :param line: The line to intersect the plane
        :return: Point at which the intersection occurs
        """
        if Vector3D.check_orthogonal(Vector3D(self.a, self.b, self.c), line.directional_vector):
            raise ParallelError("Plane and Line are parallel. An intersection point is therefore not possible")

        # Zähler
        numerator = self.d - \
                    self.a * line.support_vector.x_dir - \
                    self.b * line.support_vector.y_dir - \
                    self.c * line.support_vector.z_dir

        # Nenner
        denominator = self.a * line.directional_vector.x_dir + \
                      self.b * line.directional_vector.y_dir + \
                      self.c * line.directional_vector.z_dir

        r_val = numerator / denominator
        int_point = line.support_vector.coords + r_val * line.directional_vector.coords
        return Point3D(int_point[0], int_point[1], int_point[2])

    @staticmethod
    def from_vectors(support_vector: Vector3D, dir_vector_1: Vector3D, dir_vector_2: Vector3D) -> Plane3D:
        """
        Construct a plane from a suppor vector and two directional vectors.
        Directional vectors must not be parallel
        :param support_vector: Support vector for the plane
        :param dir_vector_1: First directinoal vector
        :param dir_vector_2: Second directional vector
        :return: The constructed plane
        """
        # Check if directional vectors are parallel -> impossible to construct plane
        if Vector3D.check_parallel(dir_vector_1, dir_vector_2):
            raise ParallelError("Directional vectors dir_vector_1 and dir_vector_2 must not be parallel")

        normal = np.cross(dir_vector_1.coords, dir_vector_2.coords)
        a, b, c = normal
        d = a * support_vector.x_dir + b * support_vector.y_dir + c * support_vector.z_dir
        return Plane3D(a, b, c, d)
