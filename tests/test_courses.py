import unittest

from canvasapi import Canvas
from app.courses import Course
from app.models import Assignment
from app import app, db
from tests import settings


def setUpModule():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    db.create_all()

    a1 = Assignment(title='Some assignment 1', course_id=1, outcome_id=123)
    a2 = Assignment(title='Some assignment 2', course_id=1, outcome_id=456)
    db.session.add_all([a1, a2])
    db.session.commit()


def tearDownModule():
    db.session.remove()
    db.drop_all()


class TestCourses(unittest.TestCase):

    def setUp(self):

        self.canvas = Canvas(settings.BASE_URL, settings.API_KEY)

        class CourseDict(dict):
            pass

        self.course = CourseDict()

        self.course.id = 1
        self.course.name = "Demo"
        self.course.sis_course_id: None
        self.course.uuid = "WvAHhY5FINzq5IyRIJybGeiXyFkG3SqHUPb7jZY5"
        self.course.integration_id = None
        self.course.sis_import_id = 34
        self.course.start_at = "2018-06-01T00:00:00Z"
        self.course.created_at = "2020-05-25T00:00:00Z"

    def test_process_course_return(self):
        processed = Course.process_course(self.course)
        self.assertIsNotNone(processed)

    def test_process_course_structure(self):
        expected = {
            "id": 1,
            "name": "Demo",
            "outcomes": 2,
            "term": 2018
        }

        processed = Course.process_course(self.course)
        self.assertDictEqual(processed, expected)

    def test_course_with_no_start_date(self):
        expected = {
            "id": 1,
            "name": "Demo",
            "outcomes": 2,
            "term": 2020
        }

        self.course.start_at = None
        processed = Course.process_course(self.course)
        self.assertDictEqual(processed, expected)
