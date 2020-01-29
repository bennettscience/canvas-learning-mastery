import json
from app import db
from app.models import Assignment, Outcome


class Assignments:
    def __init__(self, canvas, course_id):
        self.canvas = canvas
        self.course_id = course_id

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
        outcome_list = []
        json_data = []

        # Get the Course object
        course = canvas.get_course(course_id)

        if "section_id" in kwargs:
            course = course.get_section(kwargs.get("section_id"))

        # Find assignments which are aligned to Outcomes
        query = Assignment.query.filter(
            Assignment.course_id == course_id, Assignment.outcome_id.isnot(None)
        )

        if query.all():
            # Loop Item queries
            for item in query:
                # Store the Query objects as dictionaries in a list
                outcome_list.append(item.__dict__)

                # Store assignment IDs to pass to Canvas
                assignment_list.append(item.id)

            # get active students to request submissions, store IDs in a list
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

                        # Build the dictionary keys
                        canvas_id = canvas_id = item.user["id"]
                        sis_id = item.user["login_id"]
                        user_name = item.user["sortable_name"]

                        submissions.append(
                            Assignments.process_enrollment_submissions(item)
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
        student_list = []

        enrollments = course.get_enrollments(role="StudentEnrollment", state="active")

        for e in enrollments:
            item = json.loads(e.to_json())
            student_list.append(item["user"]["id"])

        return student_list

    @classmethod
    def process_enrollment_submissions(self, item):
        """ Process a student submission object
        :param item: Submission dict
        :returns submission: dict
        """
        # Get the outcome ID if it matches the assignment ID
        outcome_id = Outcome.query.get(
            Assignment.query.get(item.assignment_id).outcome_id
        ).outcome_id

        submission = {
            outcome_id: {
                "assignment_id": item.assignment_id,
                "assignment_name": item.assignment["name"],
                "assignment_score": item.score,
                "outcome_id": outcome_id,
            }
        }

        return submission

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

    @classmethod
    def build_assignment_rubric_results(self, canvas, course_id, assignment_id):

        course = canvas.get_course(course_id)

        # Get an assignment by ID
        assignment = course.get_assignment(assignment_id)

        # Use the assignment to get a rubric ID for keys/ID
        rubric = assignment.rubric

        # build a list
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
        student_results = []
        # Get submissions for the assignment to get rubric evals
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
