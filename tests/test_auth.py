import unittest
from app.auth import Auth


class TestAuth(unittest.TestCase):

    def test_login_tuple(self):
        auth_url = Auth.login()
        self.assertIsInstance(auth_url, object)
    
    def test_login_url(self):
        auth_url = Auth.login()
        self.assertIsNotNone(auth_url)
