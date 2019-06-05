import json, pprint
import multiprocessing as mp
from functools import partial
from app import app, db, logging
from app.models import Outcome, Assignment, User
from flask_login import current_user

class Outcomes:

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

        # Instantiate a list to hold return data
        data = []

        course = canvas.get_course(course_id)
        outcome_groups = course.get_outcome_groups_in_context()

        # All Outcome linked assignments should be in one group
        assignment_group = course.get_assignment_group(assignment_group_id, include=['assignments'])

        # Loop through each outcome group individually
        for group in outcome_groups:

            # Get the individual outcomes within each group
            outcomes = group.get_linked_outcomes()

            # Store each outcome in the database
            for o in outcomes:
                outcome_data = o.outcome
                outcome = Outcome(id=outcome_data['id'], title=outcome_data['title'], course_id=course_id)
                app.logger.debug('New Outcome: %s', outcome)
                db.session.add(outcome)
                db.session.commit()

        for a in assignment_group.assignments:
            assignment = Assignment(id=a['id'], title=a['name'], course_id=course_id)
            data.append({'assignment_id':a['id'], 'assignment_name':a['name']})
            app.logger.debug('New Assignment: %s', assignment)
            db.session.add(assignment)
            db.session.commit()

        return data

    @staticmethod
    def process_submissions(student_id, course):

        """ Process student Outcome and Assignment scores
        :type student_id: Int
        :param student_id: Canvas ID of current student

        :type course: {Object}
        :param course: Instantiated Canvas Course object

        :raises:

        :rtype: {Object} obj
        """    
        app.logger.debug("Processing %s", student_id)

        # Instantiate a dictionary
        obj = {}
        obj['outcomes'] = []
        obj['student_id'] = student_id

        # Request all outcome rollups from Canvas
        rollups = course.get_outcome_result_rollups(
            user_ids=student_id, aggregate="course", aggregate_stat="mean")

        # Limit to scores only
        raw_data = rollups['rollups'][0]['scores']

        # Run through each Outcome
        for outcome in raw_data:
            outcome_id = int(outcome['links']['outcome'])
            outcome_score = outcome['score']

            # Find the matched assignment in the database
            query = Assignment.query.filter_by(outcome_id=outcome_id).first()

            if query is not None:
                assignment_id = query.id

                # Get the assignment and submissions for the student
                assignment = course.get_assignment(assignment_id)
                submission = assignment.get_submission(student_id)

                app.logger.info('Submission for %s: %s', assignment_id, submission.score)

                # Instantiate an object for the current Outcome/Assignment pair
                item = {'outcome_id': outcome_id,
                        'outcome_score': outcome_score, 'assignment_id': assignment_id}

                # Set a None score to 0
                if submission.score is None:
                    submission.score = 0

                # Check the conditions and update the Canvas gradebook
                if outcome['score'] >= 3 and submission.score == 0.0:
                    item['assignment_score'] = 1
                    submission.edit(submission={'posted_grade': 1})
                elif outcome['score'] < 3 and submission.score >= 1.0:
                    item['assignment_score'] = 0
                    submission.edit(submission={'posted_grade': 0})
                else:
                    item['assignment_score'] = submission.score

                # Store the item in the return object array
                obj['outcomes'].append(item)

        return obj

    @classmethod
    def update_student_scores(cls, canvas, course_id, student_ids):

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
        # Start a pool to speed up the requests
        pool = mp.Pool(mp.cpu_count())

        course = canvas.get_course(course_id)

        # define args for the processing function
        items = partial(cls.process_submissions, course=course)

        # Post the list to the process function, wait for the results
        result = pool.map(items, student_ids)

        return result

class Assignments:

    @staticmethod
    def get_all_assignment_scores(canvas, course_id):

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
        app.logger.debug('Requested course: %s', course_id)

        # Find assignments which are aligned to Outcomes
        query = Assignment.query.filter(Assignment.course_id == course_id, Assignment.outcome_id != None)

        if query.all():

            # Loop Item queries
            for item in query:
                # Store the Query objects as dictionaries in a list
                outcome_list.append(item.__dict__)
                # Store assignment IDs to pass to Canvas
                assignment_list.append(item.id)

            app.logger.debug('Assignments: %s', assignment_list)

            # get active students to request submissions for
            enrollments = course.get_enrollments(role='StudentEnrollment')
            for e in enrollments:
                item = json.loads(e.to_json())
                student_list.append(item['user']['id'])

            app.logger.debug('Requested student list: %s', student_list)

            # Request the submissions from Canvas sorted by user
            submissions = course.get_multiple_submissions( \
                assignment_ids=assignment_list, student_ids='all', include=('user', 'assignment'), grouped=1)

            # Process the Submissions into usable JSON objects
            for sub in submissions:
                item = json.loads(sub.to_json())
                # app.logger.debug('Item JSON created')

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
