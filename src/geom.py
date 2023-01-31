"""
A module for handling geometries in 3D space
"""
from __future__ import annotations
from numbers import Real
import numpy as np


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
