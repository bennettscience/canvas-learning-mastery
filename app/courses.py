from canvasapi import Canvas
from app import app


class Courses(object):

    canvas = Canvas(
        "https://elkhart.instructure.com/", app.config["API"]["canvas"]["key"]
    )

    def __init__(cls, course_id):
        course_id = course_id

    @classmethod
    def get_course(cls, course_id):
        return cls.canvas.get_course(course_id)
