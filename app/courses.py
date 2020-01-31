from datetime import datetime

from app.models import Assignment


class Course(object):
    def __init__(self, course):
        self.course = course

    def process_course(course):
        """ Find aligned Outcomes for a requested course
        Take in a Canvas Course object and pare it down to a simple dictionary. This
        is used to load only the necessary data on the user dashboard.

        :param course: canvasapi Course
        :ptype: object

        :returns: processed dict
        """

        query = Assignment.query.filter(Assignment.course_id == course.id).filter(
            Assignment.outcome_id.isnot(None)
        )

        processed = {}
        processed["id"] = course.id
        processed["name"] = course.name
        processed["outcomes"] = query.count()

        if course.start_at is not None:
            processed["term"] = datetime.strptime(
                course.start_at, "%Y-%m-%dT%H:%M:%SZ"
            ).year
        else:
            processed["term"] = datetime.strptime(
                course.created_at, "%Y-%m-%dT%H:%M:%SZ"
            ).year

        return processed
