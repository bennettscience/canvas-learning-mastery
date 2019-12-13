import unittest

from app import app, db
from app.models import Outcome, Assignment
from sqlalchemy.orm.session import make_transient


def setUpModule():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    db.create_all()


def tearDownModule():
    db.session.remove()
    db.drop_all()


class TestAddOutcomes(unittest.TestCase):
    # @classmethod
    # def setUpClass(cls):
    #     app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    #     db.create_all()

    # @classmethod
    # def tearDownClass(cls):
    #     db.session.remove()
    #     db.drop_all()

    def test_add_single_outcome(self):
        o1 = Outcome(title='Some outcome 1', course_id=999, outcome_id=123)
        db.session.add(o1)
        db.session.commit()

    def test_add_duplicate_outcomes(self):
        o1 = Outcome(title='Some outcome 1', course_id=999, outcome_id=123)
        o2 = Outcome(title='Some outcome 1', course_id=888, outcome_id=123)
        db.session.add_all([o1, o2])
        db.session.commit()

    def test_align_outcome_to_assignment(self):
        a1 = Assignment(id=123456, title='Some assignment', course_id=999)
        o1 = Outcome(title='Some outcome 1', course_id=999, outcome_id=123)
        db.session.add(a1)
        db.session.commit()

        o1 = Outcome.query.filter_by(outcome_id=123).first()
        o1.align(a1)


class TestFindOutcomes(unittest.TestCase):
    # def setUp(self):
    pass


class TestMigrateOutcomes(unittest.TestCase):
    def test_migrate_outcomes(self):
        o1 = Outcome(title='Some outcome 1',
                     course_id=999, outcome_id=None)
        o2 = Outcome(title='Some outcome 2',
                     course_id=888, outcome_id=None)
        db.session.add_all([o1, o2])
        db.session.commit()

        outcomes = Outcome.query.all()
        for outcome in outcomes:
            db.session.expunge(outcome)
            make_transient(outcome)

            outcome.outcome_id = outcome.id
            outcome.id = None

            db.session.add(outcome)
        db.session.commit()
