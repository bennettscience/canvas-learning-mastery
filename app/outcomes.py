from canvasapi import Canvas
from pprint import pprint
import json
from pathos.multiprocessing import ProcessingPool as Pool
from functools import partial
from app import app, db
from app.models import Outcome, Assignment
from app.errors import FailedJob

from sqlalchemy import exc

# from flask_login import current_user


class Outcomes:
    def __init__(self):
        pass

    @classmethod
    def align_assignment_to_outcome(self, course_id, outcome_id, assignment_id):

        try:
            outcome = Outcome.query.filter_by(
                outcome_id=outcome_id, course_id=course_id
            ).first()
            assignment = Assignment.query.filter_by(
                id=assignment_id, course_id=course_id
            ).first()

            outcome.align(assignment)
            db.session.commit()
        except KeyError as e:
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

        # Instantiate a dictionary
        obj = {}
        obj["outcomes"] = []
        obj["student_id"] = student_id

        # Request all outcome rollups from Canvas
        rollups = course.get_outcome_result_rollups(
            user_ids=student_id,
            aggregate="course",
            aggregate_stat="mean",
            outcome_ids=outcome_ids,
        )

        # Limit to scores only
        raw_data = rollups["rollups"][0]["scores"]

        # Run through each Outcome
        for outcome in raw_data:
            outcome_id = int(outcome["links"]["outcome"])
            outcome_score = outcome["score"]

            # Find the matched assignment in the database
            # query = Assignment.query.filter_by(outcome_id=outcome_id).first()
            query = Outcome.query.filter_by(outcome_id=outcome_id).first()

            if query is not None:
                app.logger.debug(f"Assignment for {query.id}: {query.assignment[0].id}")

                assignment_id = query.assignment[0].id

                # Get the assignment and submissions for the student
                assignment = course.get_assignment(assignment_id)
                submission = assignment.get_submission(student_id)

                # Instantiate an object for the current Outcome/Assignment pair
                item = {
                    "outcome_id": outcome_id,
                    "outcome_score": outcome_score,
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

                # Store the item in the return object array
                obj["outcomes"].append(item)
            else:
                pass

        return obj

    @classmethod
    def request_score_update(self, student_id, course, outcome_ids):
        try:
            return self.process_submissions(student_id, course, outcome_ids)
        except Exception as ex:
            raise FailedJob(student_id) from ex

    @classmethod
    def update_student_scores(self, canvas, course_id, student_ids, outcome_ids):

        """ Description
        :type cls: Object
        :param cls: Outcomes class

        :type canvas: Object
        :param canvas: Canvas object

        :type course_id: Int
        :param course_id: Current course ID

        :type student_ids: List
        :param student_ids: Student IDs to iterate

        :raises:

        :rtype: List result
        """
        chunksize = 5
        total_jobs = len(student_ids)
        course = canvas.get_course(course_id)

        with Pool() as pool:

            # define args for the processing function
            job = partial(
                self.request_score_update, course=course, outcome_ids=outcome_ids
            )

            # Set an iterator to track for processing
            iter_ = pool.imap(job, student_ids)

            while True:
                completed = []
                while len(completed) < chunksize:
                    try:
                        result = next(iter_)
                    except StopIteration:
                        print("all child jobs completed")
                        # only break out of inner loop, might still be some completed
                        # jobs to dispatch
                        break
                    except FailedJob as ex:
                        print("processing of {} job failed".format(ex.args[0]))
                    else:
                        completed.append(result)

                if completed:
                    print("completed:", completed)
                    # put your dispatch logic here
                    result = [r for r in iter_ if r is not None]
                    return result

                if len(completed) < chunksize:
                    print("all jobs completed")

    @classmethod
    def get_student_rollups(self, course_id, student_id):

        course = self.canvas.get_course(course_id)

        data = course.get_outcome_result_rollups(user_ids=student_id)
        return data
