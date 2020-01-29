import unittest
from canvasapi import Canvas

from app import app, db
from app.models import Assignment, Outcome
from app.assignments import Assignments
from tests import settings


class TestAssignments(unittest.TestCase):
    def setUp(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
        db.create_all()

        self.canvas = Canvas(settings.BASE_URL, settings.API_KEY)
        self.course_id = 39775
        self.assignment_id = 190160
        self.assignment_group = 40777

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_assignment(self):
        a1 = Assignment(id=1, title="Some assignment 1", outcome_id="")
        a2 = Assignment(id=2, title="Some assignment 2", outcome_id="")
        db.session.add_all([a1, a2])
        db.session.commit()

    def test_save_assignment_data(self):
        Assignments.save_assignment_data(
            self.canvas, self.course_id, self.assignment_group
        )
        query = Assignment.query.all()
        self.assertEqual(len(query), 15)

    def test_alignments(self):
        assignments = Assignment.query.all()
        for a in assignments:
            Outcome.is_aligned(a)

    def test_create_alignment(self):
        a1 = Assignment(id=1, title="Some assignment 1", outcome_id="")
        o1 = Outcome(id=123, title="Some outcome 1")
        db.session.add_all([a1, o1])
        db.session.commit()
        o1.align(a1)

    def test_get_assignment_rubric_results(self):
        cols_expected = [
            {
                "id": "7065_8592",
                "name": "G.PL.3",
                "outcome_id": 15300
            },
            {
                "id": "7065_7537",
                "name": "G.T.1",
                "outcome_id": 15303
            }
        ]
        result = Assignments.build_assignment_rubric_results(
            self.canvas, self.course_id, self.assignment_id
        )
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result['columns'], list)
        self.assertIsInstance(result['student_results'], list)
        self.assertEqual(result['columns'], cols_expected)

    def test_get_course_assignments(self):
        course_id = 37656
        result = Assignments.get_course_assignments(self.canvas, course_id)
        self.assertIsInstance(result, list)

    def test_build_enrollment_list(self):
        course = self.canvas.get_course(self.course_id)
        enrollments = Assignments.build_enrollment_list(course)

        self.assertIsInstance(enrollments, list)
        self.assertEqual(len(enrollments), 2)

    def test_build_submission_dict(self):
        o1 = Outcome(id=1, title='Test Outcome', course_id=39775, outcome_id=123)
        a1 = Assignment(id=190128, title='Test Assignment', course_id=39775)
        db.session.add_all([o1, a1])
        db.session.commit()

        o1.align(a1)
        db.session.commit()

        course = self.canvas.get_course(self.course_id)
        enrollments = [31874, 31875]
        assignment_list = [190128]
        submissions = []

        all_submissions = course.get_multiple_submissions(
            assignment_ids=assignment_list,
            student_ids=enrollments,
            include=("user", "assignment"),
            grouped=True,
        )

        for student in all_submissions:
            items = student.submissions
            for item in items:
                submissions.append(Assignments.process_enrollment_submissions(item))

        self.assertIsInstance(submissions, list)
