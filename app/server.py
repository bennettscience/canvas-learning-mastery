import json, pprint
from app import app, db, logging
from app.models import Outcome, Assignment, User
from flask_login import current_user

class Outcomes:

    @staticmethod
    def save_course_data(canvas, course_id):

        data = []
        course = canvas.get_course(course_id)
        outcome_groups = course.get_outcome_groups_in_context()

        # All Outcome linked assignments should be in one group
        assignment_group = course.get_assignment_group(app.config['OUTCOME_ASSIGNMENTS'], include=['assignments'])

        for g in outcome_groups:
            outcomes = g.get_linked_outcomes()
            for o in outcomes:
                outcome_data = o.outcome
                outcome = Outcome(id=outcome_data['id'], title=outcome_data['title'])
                print("New Outcome {}".format(outcome))
                db.session.add(outcome)

        for a in assignment_group.assignments:
            assignment = Assignment(id=a['id'], title=a['name'])
            data.append({'assignment_id':a['id'], 'assignment_name':a['name']})
            db.session.add(assignment)

        db.session.commit()
        return data
    
    @staticmethod
    def make_outcome_dict(canvas, course_id):
        """ Create a dictionary of Outcomes from the course ID """
        data = []
        course = canvas.get_course(course_id)
        groups = course.get_outcome_groups_in_context()

        for g in groups:
            outcomes = g.get_linked_outcomes()
            for o in outcomes:
                outcome = o.outcome
                data.append({'outcome_id': outcome['id'], 'outcome_title':outcome['title']})

        return data

    @staticmethod
    def get_user_outcomes(canvas, course_id, student_id_list):
        """ Get outcomes for all students in a given course """
        data = []
        course = canvas.get_course(course_id)

        print(student_id_list)

        for student in student_id_list:
            print(student)
            outcomes = []
            rollups = course.get_outcome_result_rollups(user_ids=student, aggregate="course", aggregate_stat="mean")

            raw_data = rollups['rollups'][0]['scores']

            for outcome in raw_data:
                outcome_id = int(outcome['links']['outcome'])
                outcome_score = outcome['score']

                query = Assignment.query.filter_by(outcome_id=outcome_id).first()
                if query is not None:
                    assignment_id = query.id

                outcome = {'outcome_id': outcome_id, 'outcome_score': outcome_score, 'assignment_id': assignment_id}
                outcomes.append(outcome)

            data.append({
                'student_id': student,
                'outcomes': outcomes,
            })

        return data

class Assignments:

    @staticmethod
    def get_all_assignment_scores(canvas, course_id):

        # make a couple lists to hold processed data
        assignment_list = []
        student_list = []
        outcome_list = []
        json_data = []

        course = canvas.get_course(course_id)
        app.logger.info('Requested course: %s', course)

        # Find assignments which are aligned to Outcomes
        query = Assignment.query.filter(Assignment.outcome_id != None)

        if query.all():

            # Loop Item queries
            for item in query:
                # Store the Query objects as dictionaries in a list
                outcome_list.append(item.__dict__)
                # Store assignment IDs to pass to Canvas
                assignment_list.append(item.id)

            # get active students to request submissions for
            enrollments = course.get_enrollments(role='StudentEnrollment')
            for e in enrollments:
                item = json.loads(e.to_json())
                student_list.append(item['user']['id'])

            app.logger.info('Requested list: %s', student_list)

            # Request the submissions from Canvas sorted by user
            submissions = course.get_multiple_submissions( \
                assignment_ids=assignment_list, student_ids='all', include=('user', 'assignment'), grouped=1)

            # Process the Submissions into usable JSON objects
            for sub in submissions:
                item = json.loads(sub.to_json())

                if item['submissions']:
                    if item['user_id'] in student_list:
                        canvas_id = item['user_id']
                        sis_id = item['submissions'][0]['user']['login_id']
                        user_name = item['submissions'][0]['user']['name']
                        submissions = []

                        for assignment in item['submissions']:
                            assignment_score = assignment['grade']
                            assignment_id = assignment['assignment']['id']
                            assignment_name = assignment['assignment']['name']

                            outcome_id = [int(val['outcome_id']) for val in outcome_list if val['id'] == assignment_id]

                            submissions.append({
                                'assignment_id': assignment_id,
                                'assignment_name': assignment_name,
                                'assignment_score': assignment_score,
                                'outcome_id': int(outcome_id[0])
                            })

                        json_data.append({
                            'canvas_id': canvas_id,
                            'sis_id': sis_id,
                            'user_name': user_name,
                            'submissions': submissions,
                        })
            else:
                return None

        return json_data
