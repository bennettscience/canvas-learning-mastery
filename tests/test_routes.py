import unittest
from app import app
from flask import template_rendered

from contextlib import contextmanager

# https://stackoverflow.com/questions/23987564/test-flask-render-template-context
@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


class TestRoutes(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        self.course_id = 39775

    def tearDown(self):
        pass

    def test_index_logged_out(self):
        with captured_templates(app) as templates:
            resp = self.client.get('/')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(templates), 1)
            template, context = templates[0]
            self.assertEqual(template.name, 'login.html')

    def test_dashboard_logged_out(self):
        # redireect the user to the login screen
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 302)

    def test_logout(self):
        # Redirect the user back to the login screen
        resp = self.client.get('/logout')
        self.assertEqual(resp.status_code, 302)

    def test_course_no_id(self):
        resp = self.client.get('/course')
        self.assertEqual(resp.status_code, 404)

    def test_course_logged_out(self):
        resp = self.client.get(f'course/{self.course_id}')
        self.assertEqual(resp.status_code, 302)

    def test_logged_out_course_with_id(self):
        with captured_templates(app) as templates:
            resp = self.client.get(f'/course/{self.course_id}')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(templates), 1)
            template, context = templates[0]
            self.assertEqual(template.name, 'course.html')
