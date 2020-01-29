import unittest
from canvasapi import Canvas

from app import app, db
from app.models import Outcome, Assignment
from app.outcomes import Outcomes
from tests import settings


def setUpModule():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    db.create_all()

    o1 = Outcome(title='Some outcome 1', course_id=999, outcome_id=123)
    o2 = Outcome(title='Some outcome 1', course_id=888, outcome_id=123)
    db.session.add_all([o1, o2])
    db.session.commit()


def tearDownModule():
    db.session.remove()
    db.drop_all()


class TestAddOutcomes(unittest.TestCase):

    def setUp(self):
        self.canvas = Canvas(settings.BASE_URL, settings.API_KEY)

    def tearDown(self):
        pass

    def test_add_single_outcome(self):
        o1 = Outcome(title='Some outcome 1', course_id=999, outcome_id=123)
        db.session.add(o1)
        db.session.commit()

    def test_add_duplicate_outcomes(self):
        o1 = Outcome(title='Some outcome 1', course_id=999, outcome_id=123)
        o2 = Outcome(title='Some outcome 1', course_id=888, outcome_id=123)
        db.session.add_all([o1, o2])
        db.session.commit()

    def test_query_outcomes(self):
        outcome = Outcome.query.filter_by(outcome_id=123).first()
        self.assertIs(outcome.outcome_id, 123)

    def test_align_outcome_to_assignment(self):
        a1 = Assignment(id=123456, title='Some assignment', course_id=999)
        db.session.add(a1)
        db.session.commit()

        o1 = Outcome.query.filter_by(outcome_id=123).first()
        o1.align(a1)

    def test_add_outcomes_from_canvas(self):
        Outcomes.save_outcome_data(self.canvas, 39830)
        outcomes = Outcome.query.filter_by(course_id=39830).all()
        self.assertEqual(len(outcomes), 2)


class TestAlignOutcomes(unittest.TestCase):

    def setUp(self):
        a1 = Assignment(id=999, title="Some Assignment")
        db.session.add(a1)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_align_assignment_to_outcome(self):
        o3 = Outcome(outcome_id=1, course_id=999, title="Test Outcome 1")
        db.session.add(o3)
        db.session.commit()

        outcome_id = 1
        assignment_id = 999
        Outcomes.align_assignment_to_outcome(outcome_id, assignment_id)

        outcome = Outcome.query.filter_by(outcome_id=1).first()
        self.assertIsNotNone(outcome.assignment_id)
