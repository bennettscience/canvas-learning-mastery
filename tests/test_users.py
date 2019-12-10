import unittest

from app import app, db
from app.models import User


def setUpModule():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    db.create_all()


def tearDownModule():
    db.session.remove()
    db.drop_all()


class TestUsers(unittest.TestCase):
    def test_new_user(self):
        u1 = User(id=1, canvas_id=123, name='Brian Bennett', token='123456abcd')
        db.session.add(u1)
        db.session.commit()
