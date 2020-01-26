from canvasapi import Canvas
import unittest
from app.courses import Courses

from app import app


class TestCourses(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas(
            "https://elkhart.instructure.com/", app.config["API"]["canvas"]["key"]
        )

    def test_get_course_as_object(self):
        course = Courses.get_course(33159)
        self.assertIsInstance(course, object)

    def test_get_course_name(self):
        course = Courses.get_course(33159)
        self.assertEqual(course.name, 'SIOP')
