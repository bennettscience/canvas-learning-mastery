import unittest
from canvasapi import Canvas
from app import app, db
from app.models import Outcome, Assignment, User
from app.server import Assignments

# class TestUser(unittest.TestCase):

#     def setUp(self):
#         app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
#         db.create_all()

#     def tearDown(self):
#         db.session.remove()
#         db.drop_all()

#     def test_new_user(self):
#         u1 = User(id=1, canvas_id=123, name='Brian Bennett')
#         db.session.add(u1)
#         db.session.commit()


class TestOutcomes(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_outcome(self):
        o1 = Outcome(id=123, title='Some outcome 1', course_id=999)
        o2 = Outcome(id=456, title='Some outcome 2', course_id=888)
        db.session.add_all([o1, o2])
        db.session.commit()


class TestAssignments(unittest.TestCase):

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_assignment(self):
        a1 = Assignment(id=1, title='Some assignment 1', outcome_id='')
        a2 = Assignment(id=2, title='Some assignment 2', outcome_id='')
        db.session.add_all([a1, a2])
        db.session.commit()

    def test_alignments(self):
        assignments = Assignment.query.all()
        for a in assignments:
            Outcome.is_aligned(a)

    def test_create_alignment(self):
        a1 = Assignment(id=1, title='Some assignment 1', outcome_id='')
        o1 = Outcome(id=123, title='Some outcome 1')
        db.session.add_all([a1, o1])
        db.session.commit()

        o1.align(a1)

    def test_get_rubric_result_for_assignment(self):
        course_id = 36756
        assignment_id = 166466
        canvas = Canvas('https://elkhart.instructure.com/', app.config['API']['canvas']['key'])
        result = Assignments.get_rubric_result_for_assignment(
            canvas, course_id, assignment_id)
        self.assertIsInstance(result, list)

    def test_get_course_assignments(self):
        course_id = 37656
        canvas = Canvas('https://elkhart.instructure.com', app.config['API']['canvas']['key'])

        result = Assignments.get_course_assignments(canvas, course_id)
        self.assertIsInstance(result, list)

if __name__ == '__main__':
    unittest.main(verbosity=2)
