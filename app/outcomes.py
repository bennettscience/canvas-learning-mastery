import concurrent.futures
from functools import partial

from app import db
from app.models import Outcome, Assignment
from app.errors import FailedJob


class Outcomes:
    """ Methods for working with Canvas outcomes """

    def __init__(self):
        pass

    @classmethod
    def align_assignment_to_outcome(self, course_id, outcome_id, assignment_id):
        """
        Aligns an assignment ID to an outcome ID
        :param course_id: Canvas course ID
        :ptype: int

        :param outcome_id: Canvas Outcome ID
        :ptype: int

        :param assignment_id: Canvas Assignment ID
        :ptype: int

        :raises Exception: exception object
        :rtype: None
        """

        try:
            outcome = Outcome.query.filter_by(
                outcome_id=outcome_id, course_id=course_id
            ).first()
            assignment = Assignment.query.filter_by(
                id=assignment_id, course_id=course_id
            ).first()
            if all(v is not None for v in [outcome, assignment]):
                print(f"Aligning {outcome} to {assignment}")
                outcome.align(assignment)
                db.session.commit()
            else:
                raise AttributeError(
                    f"{assignment_id} is not a valid assignment ID for this course."
                )
        except Exception as e:
            return e

    @staticmethod
    def save_outcome_data(canvas, course_id):
        """ Get Outcomes from Canvas for the course and store them in the database

        :param canvas: Canvas object
        :type canvas: Object

        :param course_id: Canvas course ID
        :type course_id: int

        :param assignment_group_id: Assignment group to update
        :type assignment_group_id: Int

        :returns data: List of all assignments stored from the assignment group
        :rtype: List data
        """
        course = canvas.get_course(course_id)
        outcome_groups = course.get_outcome_groups_in_context()

        outcome_commits = []
        for group in outcome_groups:

            outcomes = group.get_linked_outcomes()

            for o in outcomes:
                outcome_data = o.outcome
                query = Outcome.query.filter_by(
                    outcome_id=outcome_data["id"], course_id=course_id
                )

                if query.first() is None:
                    outcome = Outcome(
                        outcome_id=outcome_data["id"],
                        title=outcome_data["title"],
                        course_id=course_id,
                    )

                    outcome_commits.append(outcome)

        db.session.bulk_save_objects(outcome_commits)
        db.session.commit()

    @classmethod
    def process_submissions(self, student_id, course, outcome_ids):
        """ Process student Outcome and Assignment scores
        :type student_id: Int
        :param student_id: Canvas ID of current student

        :type course: {Object}
        :param course: Instantiated Canvas Course object

        :raises:

        :rtype: {Object} obj
        """

        obj = {}
        obj["outcomes"] = []
        obj["student_id"] = student_id

        # Request all outcome rollups from Canvas for each student
        request = course.get_outcome_result_rollups(
            user_ids=student_id,
            outcome_ids=outcome_ids,
        )

        # Limit to scores only
        scores = request["rollups"][0]["scores"]

        for outcome in scores:
            outcome_id = int(outcome["links"]["outcome"])

            # Find the matched assignment in the database
            query = Outcome.query.filter_by(
                outcome_id=outcome_id, course_id=course.id
            ).first()

            if query is not None:
                assignment_id = query.assignment[0].id

                assignment = course.get_assignment(assignment_id)
                submission = assignment.get_submission(student_id)

                item = {
                    "outcome_id": outcome_id,
                    "outcome_score": outcome['score'],
                    "assignment_id": assignment_id,
                }

                # Set a None score to 0
                if submission.score is None:
                    submission.score = 0

                # Check the conditions and update the Canvas gradebook
                if outcome["score"] >= 2.80 and submission.score == 0:
                    item["assignment_score"] = 1
                    submission.edit(submission={"posted_grade": 1})
                elif outcome["score"] < 2.80 and submission.score >= 1:
                    item["assignment_score"] = 0
                    submission.edit(submission={"posted_grade": 0})
                elif outcome["score"] < 2.80 and submission.score == 0:
                    item["assignment_score"] = 0
                    submission.edit(submission={"posted_grade": 0})
                else:
                    item["assignment_score"] = submission.score

                obj["outcomes"].append(item)
            else:
                pass
        
        db.session.close()
        return obj

    @classmethod
    def request_score_update(self, student_id, course, outcome_ids):
        """ Post grade updates to Canvas for a student
        :param student_id: Valid Canvas student ID
        :ptype: int

        :param course: canvasapi <Course> object
        :ptype: <Course>

        :param outcome_ids: Outcome IDs to request from Canvas for processing
        :ptype: list of int

        :raises: Exception <FailedJob>

        :returns update: outcome ID, assignment ID, and updated score
        :rtype: dict
        """
        try:
            update = self.process_submissions(student_id, course, outcome_ids)
            return update

        except Exception as ex:
            raise FailedJob(ex)

    @classmethod
    def update_student_scores(self, canvas, course_id, student_ids, outcome_ids):
        """ Worker to process assignment scores for students
        :param cls: Outcomes class
        :ptype cls: <Outcome> instance

        :param canvas: Canvas object
        :ptype canvas: <Canvas> instance

        :param course_id: Current course ID
        :ptype course_id: Int

        :param student_ids: Student IDs to iterate
        :ptype student_ids: list of int

        :raises:

        :returns data: List of assignment update objects for a student
        :rtype: list of dicts
        """
        # start = time.perf_counter()
        course = canvas.get_course(course_id)

        job = partial(self.request_score_update, course=course, outcome_ids=outcome_ids)

        data = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(job, student_ids)

            for result in results:
                data.append(result)

        return data

    @classmethod
    def get_student_rollups(self, course_id, student_id):
        """ Request student outcome rollups from Canvas

        :param course_id: Valid Canvas course ID
        :type course_id: int

        :param student_id: Valid Canvas ID for a student
        :type student_id: int

        :return: Outcome result rollups from Canvas
        :rtype: list of dict
        """
        course = self.canvas.get_course(course_id)

        data = course.get_outcome_result_rollups(user_ids=student_id)
        return data
