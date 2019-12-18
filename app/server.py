from canvasapi import Canvas
from pprint import pprint
import json
from pathos.multiprocessing import ProcessingPool as Pool
from functools import partial
from app import app, db
from app.models import Outcome, Assignment
from app.errors import FailedJob

# from flask_login import current_user


class Outcomes:
    def __init__(self, canvas):
        self.canvas = canvas

    @staticmethod
    def save_course_data(canvas, course_id, assignment_group_id):

        """ Get Outcomes from Canvas for the course and store them in the database

        :type canvas: Object
        :param canvas: Canvas object

        :type course_id: Int
        :param course_id: Canvas course ID

        :type assignment_group_id: Int
        :param assignment_group_id: Assignment group to update

        :rtype: List data
        """
        data = []
        app.logger.debug(course_id)

        course = canvas.get_course(course_id)
        outcome_groups = course.get_outcome_groups_in_context()

        # All Outcome linked assignments should be in one group
        assignment_group = course.get_assignment_group(
            assignment_group_id, include=["assignments"]
        )

        # Loop through each outcome group individually
        for group in outcome_groups:

            # Get the individual outcomes within each group
            outcomes = group.get_linked_outcomes()

            # Store each outcome in the database
            for o in outcomes:
                outcome_data = o.outcome
                query = Outcome.query.filter_by(
                    outcome_id=outcome_data["id"], course_id=course_id
                )
                app.logger.debug(query.first())
                app.logger.debug(f"Need an outcome: {query.all() is None}")

                if query.first() is None:
                    outcome = Outcome(
                        outcome_id=outcome_data["id"],
                        title=outcome_data["title"],
                        course_id=course_id,
                    )
                    app.logger.debug("New Outcome: %s", outcome)
                    db.session.add(outcome)
                    db.session.commit()

        for a in assignment_group.assignments:
            query = Assignment.query.get(a["id"])

            if query is None:
                assignment = Assignment(
                    id=a["id"], title=a["name"], course_id=course_id
                )
                data.append({"assignment_id": a["id"], "assignment_name": a["name"]})
                app.logger.debug("New Assignment: %s", assignment)
                db.session.add(assignment)
                db.session.commit()

        return data

    @staticmethod
    def process_submissions(student_id, course, outcome_ids):

        """ Process student Outcome and Assignment scores
        :type student_id: Int
        :param student_id: Canvas ID of current student

        :type course: {Object}
        :param course: Instantiated Canvas Course object

        :raises:

        :rtype: {Object} obj
        """
        app.logger.debug("Processing %s", student_id)
        app.logger.debug("Outcomes %s", outcome_ids)

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
    def request_score_update(cls, student_id, course, outcome_ids):
        try:
            return cls.process_submissions(student_id, course, outcome_ids)
        except Exception as ex:
            raise FailedJob(student_id) from ex

    @classmethod
    def update_student_scores(cls, canvas, course_id, student_ids, outcome_ids):

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
                cls.request_score_update, course=course, outcome_ids=outcome_ids
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
    def get_student_rollups(cls, course_id, student_id):

        course = cls.canvas.get_course(course_id)

        data = course.get_outcome_result_rollups(user_ids=student_id)
        return data


class Assignments:

    # Return an error if the assignment is forbidden
    # include the assignment name
    @staticmethod
    def get_all_assignment_scores(canvas, course_id, **kwargs):

        """ Request current scores for students in the course
        :type canvas: Object
        :param canvas: Canvas object

        :type course_id: Int
        :param course_id: Canvas course ID

        :raises:

        :rtype: Object json_data
        """
        # make a couple lists to hold processed data
        assignment_list = []
        student_list = []
        outcome_list = []
        json_data = []

        # Get the Course object
        course = canvas.get_course(course_id)

        if "section_id" in kwargs:
            course = course.get_section(kwargs.get("section_id"))

        # app.logger.debug('Requested course: %s', course_id)

        # Find assignments which are aligned to Outcomes
        query = Assignment.query.filter(
            Assignment.course_id == course_id, Assignment.outcome_id != None
        )

        if query.all():

            # Loop Item queries
            for item in query:
                # Store the Query objects as dictionaries in a list
                outcome_list.append(item.__dict__)

                # Store assignment IDs to pass to Canvas
                assignment_list.append(item.id)

            app.logger.debug("Outcome list: %s", outcome_list)
            # get active students to request submissions, store IDs in a list
            enrollments = course.get_enrollments(
                role="StudentEnrollment", state="active"
            )
            for e in enrollments:
                item = json.loads(e.to_json())
                student_list.append(item["user"]["id"])

            # Request the submissions from Canvas sorted by user
            submissions = course.get_multiple_submissions(
                assignment_ids=assignment_list,
                student_ids=student_list,
                include=("user", "assignment"),
                grouped=True,
            )

            # Process the Submissions into usable JSON objects
            for submission_group in submissions:

                submissions = []

                for sub in submission_group.submissions:

                    item = json.loads(sub.to_json())

                    if item["user"]["id"] in student_list:
                        app.logger.debug(
                            "Found " + item["user"]["name"] + " in the list."
                        )
                        canvas_id = item["user"]["id"]
                        sis_id = item["user"]["login_id"]
                        user_name = item["user"]["sortable_name"]

                        assignment_score = item["grade"]
                        assignment_id = item["assignment_id"]
                        assignment_name = item["assignment"]["name"]

                        # Get the outcome ID if it matches the assignment ID
                        outcome_id = Outcome.query.get(
                            Assignment.query.get(assignment_id).outcome_id
                        ).outcome_id

                        submission = {
                            outcome_id: {
                                "assignment_id": assignment_id,
                                "assignment_name": assignment_name,
                                "assignment_score": assignment_score,
                                "outcome_id": outcome_id,
                            }
                        }

                        submissions.append(submission)

                    else:
                        continue

                json_data.append(
                    {
                        "canvas_id": canvas_id,
                        "sis_id": sis_id,
                        "user_name": user_name,
                        "submissions": submissions,
                    }
                )

        else:
            return None

        # app.logger.debug(pprint.pprint(json_data))
        return json_data

    @staticmethod
    def get_course_assignments(canvas, course_id):

        course = canvas.get_course(course_id)

        assignments = list(course.get_assignments())

        # This works without the boolean
        assignment_list = [
            {"id": assignment.id, "name": assignment.name}
            for assignment in assignments
            if hasattr(assignment, "rubric")
        ]

        return assignment_list

    def get_assignment_rubric_results(canvas, course_id, assignment_id):

        course = canvas.get_course(course_id)

        # Get an assignment by ID
        assignment = course.get_assignment(assignment_id)

        # Use the assignment to get a rubric ID for keys/ID
        rubric = assignment.rubric

        # build a list
        columns = []

        for criteria in rubric:
            if "outcome_id" in criteria:
                print(criteria)

                column = {}
                column["id"] = criteria["id"]
                column["name"] = criteria["description"]
                column["outcome_id"] = criteria["outcome_id"]
                columns.append(column)

        # Get submissions for the assignment to get rubric evals
        submissions = assignment.get_submissions(include=("rubric_assessment", "user"))

        # Create a list to store all results
        student_results = list()

        for submission in list(submissions):

            student_result = {}
            student_result["id"] = submission.user_id
            student_result["name"] = submission.user["sortable_name"]
            student_result["score"] = submission.score
            if hasattr(submission, "rubric_assessment"):
                student_result["rubric"] = submission.rubric_assessment
            student_results.append(student_result)

        student_results = sorted(student_results, key=lambda x: x["name"].split(" "))

        return {"columns": columns, "studentResults": student_results}
