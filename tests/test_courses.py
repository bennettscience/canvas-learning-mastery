from canvasapi import Canvas
import unittest
from app.courses import Course


from app import app


class TestCourses(unittest.TestCase):
    def setUp(self):
        self.courseObj = Course()

    def test_get_course_as_object(self):
        course = Course.get_course(33159)
        self.assertIsInstance(course, object)

    def test_get_course_name(self):
        course = Course.get_course(33159)
        self.assertEqual(course.name, "SIOP")

    def test_course_has_start_date(self):
        course = Course.get_course(33159)
        self.assertIsNone(course.start_at)

    def test_get_user_courses(self):
        courses = Course.get_user_courses()
        self.assertIsNotNone(courses, "Received courses for the logged in user.")

    def test_get_user_courses_as_list(self):
        courses = Course.get_user_courses()
        self.assertIsInstance(courses, list)
