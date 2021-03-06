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
    a1 = Assignment(title="Some assignment", course_id=999, id=111)
    db.session.add_all([o1, o2, a1])
    db.session.commit()


def tearDownModule():
    db.session.remove()
    db.drop_all()


class TestAddOutcomes(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()
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
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()
        o2 = Outcome(outcome_id=123, course_id=999, title="Some Outcome")
        a2 = Assignment(id=999, course_id=999, title="Some Assignment")
        db.session.add_all([o2, a2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_align_assignment_to_outcome(self):
        o3 = Outcome(outcome_id=1, course_id=999, title="Test Outcome 1")
        a1 = Assignment(title='Some Assignment', course_id=999, id=1)

        db.session.add_all([o3, a1])
        db.session.commit()

        outcome_id = 1
        assignment_id = 1
        course_id = 999
        Outcomes.align_assignment_to_outcome(course_id, outcome_id, assignment_id)

        outcome = Outcome.query.filter_by(outcome_id=1).first()
        self.assertIsNotNone(outcome.assignment_id)

    def test_unalign_outcome(self):
        o = Outcome.query.filter_by(outcome_id=123).first()
        a = Assignment.query.filter_by(id=999).first()

        o.align(a)
        db.session.commit()

        o.align(None)
        db.session.commit()

        self.assertIsNone(o.assignment_id)
