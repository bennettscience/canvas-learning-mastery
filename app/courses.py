from datetime import datetime

from app.models import Assignment


class Course(object):

    def __init__(self, course_id):
        self.course_id = course_id

    @staticmethod
    def process_courses(course):
        
        query = Assignment.query.filter(Assignment.course_id == course.id).filter(
            Assignment.outcome_id != None
        )

        processed = {}
        processed["id"] = course.id
        processed["name"] = course.name
        processed["outcomes"] = query.count()

        if course.start_at is not None:
            processed["term"] = datetime.strptime(course.start_at, "%Y-%m-%dT%H:%M:%SZ").year
        else:
            processed["term"] = datetime.strptime(course.created_at, "%Y-%m-%dT%H:%M:%SZ").year

        return processed


