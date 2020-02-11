import json
from app import db
from app.models import Assignment, Outcome


class Assignments:
    def __init__(self, canvas, course_id):
        """ Instantiate an Assignment to work with

        :param canvas: <Canvas> object to work with the API
        :type canvas: instance of <Canvas>

        :param course_id: Valid Canvas course ID
        :type course_id: int
        """
        self.canvas = canvas
        self.course_id = course_id

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
        outcome_list = []
        json_data = []

        course = canvas.get_course(course_id)

        if "section_id" in kwargs:
            course = course.get_section(kwargs.get("section_id"))

        query = Assignment.query.filter(
            Assignment.course_id == course_id, Assignment.outcome_id.isnot(None)
        )

        if query.all():

            for item in query:
                outcome_list.append(item.__dict__)
                assignment_list.append(item.id)

            enrollments = Assignments.build_enrollment_list(course)

            # Request the submissions from Canvas sorted by user in a
            # single call to speed it up.
            all_submissions = course.get_multiple_submissions(
                assignment_ids=assignment_list,
                student_ids=enrollments,
                include=("user", "assignment"),
                grouped=True,
            )

            # GroupedSubmission objects are organized by student_id. Each object
            # has a list of Submissions that need to be processed individually.
            for student in all_submissions:

                submissions = []
                items = student.submissions

                for item in items:

                    # Check that the user is still active in the course
                    if item.user["id"] in enrollments:

                        canvas_id = canvas_id = item.user["id"]
                        sis_id = item.user["login_id"]
                        user_name = item.user["sortable_name"]

                        submissions.append(
                            Assignments.process_enrollment_submissions(
                                canvas, course_id, canvas_id, item
                            )
                        )

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

        return json_data

    @classmethod
    def build_enrollment_list(self, course):
        """ Request a list of enrollments from the Canvas API for a course

        :param course: <Course> instance
        :type course: Class

        :return: List of student IDs
        :rtype: list of int
        """
        student_list = []

        enrollments = course.get_enrollments(role="StudentEnrollment", state="active")

        for e in enrollments:
            item = json.loads(e.to_json())
            student_list.append(item["user"]["id"])

        return student_list

    @classmethod
    def process_enrollment_submissions(self, canvas, course_id, student_id, item):
        """ Process a student submission object

        :param item: Submission dict
        :returns submission: dict
        """
        # Get the outcome ID if it matches the assignment ID
        outcome_id = Outcome.query.get(
            Assignment.query.get(item.assignment_id).outcome_id
        ).outcome_id

        outcome_rollup = canvas.get_course(course_id).get_outcome_result_rollups(
            user_ids=student_id, outcome_ids=outcome_id
        )

        if len(outcome_rollup["rollups"][0]["scores"]) > 0:
            score = outcome_rollup["rollups"][0]["scores"][0]["score"]
        else:
            score = None

        submission = {
            outcome_id: {
                "assignment_id": item.assignment_id,
                "assignment_name": item.assignment["name"],
                "assignment_score": item.score,
                "outcome_id": outcome_id,
                "current_outcome_score": score,
            }
        }

        return submission

    @staticmethod
    def get_course_assignments(canvas, course_id):
        """ Get all assignments for a Canvas course

        :param canvas: Instance of <Canvas>
        :type canvas: Class

        :param course_id: Valid Canvas course ID
        :type course_id: int

        :return: List of assignment IDs
        :rtype: list of int
        """
        course = canvas.get_course(course_id)

        assignments = list(course.get_assignments())

        assignment_list = [
            {"id": assignment.id, "name": assignment.name}
            for assignment in assignments
            if hasattr(assignment, "rubric")
        ]

        return assignment_list

    @classmethod
    def build_assignment_rubric_results(self, canvas, course_id, assignment_id):
        """ Look up rubric results for a specific Canvas assignment

        :param canvas: <Canvas> instance
        :type canvas: Class

        :param course_id: Valid Canvas course ID
        :type course_id: int

        :param assignment_id: Valid Canvas assignment ID
        :type assignment_id: int

        :return: Named dictionary of outcomes and rubric results for an assignment
        :rtype: dict of list of ints
        """
        course = canvas.get_course(course_id)
        assignment = course.get_assignment(assignment_id)

        rubric = assignment.rubric

        # build a list to use as headers in the view
        columns = []

        for criteria in rubric:
            if "outcome_id" in criteria:

                column = {}
                column["id"] = criteria["id"]
                column["name"] = criteria["description"]
                column["outcome_id"] = criteria["outcome_id"]
                columns.append(column)

        # Create a list to store all results
        student_results = self.get_assignment_scores(assignment)

        return {"columns": columns, "student_results": student_results}

    @classmethod
    def get_assignment_scores(self, assignment):
        """ Request assignment scores from Canvas

        :param assignment: <Assignment> instance
        :type assignment: Class

        :return: A list of student dicts with results for the assigment
        :rtype: list of dict
        """
        student_results = []

        # Get submissions for the assignment to get rubric evaluation
        submissions = assignment.get_submissions(include=("rubric_assessment", "user"))

        for submission in list(submissions):

            student_result = {}
            student_result["id"] = submission.user_id
            student_result["name"] = submission.user["sortable_name"]
            student_result["score"] = submission.score
            if hasattr(submission, "rubric_assessment"):
                student_result["rubric"] = submission.rubric_assessment
            student_results.append(student_result)

        student_results = sorted(student_results, key=lambda x: x["name"].split(" "))

        return student_results

    def save_assignment_data(canvas, course_id, assignment_group_id):
        """ Save course assignments to the database.
        :param canvas: canvasapi Canvas object
        :ptype canvas: object

        :param course_id: Canvas course ID
        :ptype course_id: int

        :param assignment_group_id: Canvas assignment group ID
        :ptype assignment_group_id: int
        """

        assignment_commits = []

        course = canvas.get_course(course_id)
        assignment_group = course.get_assignment_group(
            assignment_group_id, include=["assignments"]
        )

        for a in assignment_group.assignments:
            query = Assignment.query.get(a["id"])

            if query is None:
                assignment = Assignment(
                    id=a["id"], title=a["name"], course_id=course_id
                )

                assignment_commits.append(assignment)

        db.session.bulk_save_objects(assignment_commits)
        db.session.commit()
