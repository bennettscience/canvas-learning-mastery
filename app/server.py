from canvasapi import Canvas
from pprint import pprint
import json, pprint
import canvasapi
import multiprocessing as mp
from functools import partial
from app import app, db
from app.models import Outcome, Assignment
from werkzeug.exceptions import HTTPException
# from flask_login import current_user

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
                query = Outcome.query.get(outcome_data['id'])

                if query is None:
                    outcome = Outcome(id=outcome_data['id'], title=outcome_data['title'], course_id=course_id)
                    app.logger.debug('New Outcome: %s', outcome)
                    db.session.add(outcome)
                    db.session.commit()

        for a in assignment_group.assignments:
            query = Assignment.query.get(a['id'])

            if query is None:
                assignment = Assignment(id=a['id'], title=a['name'], course_id=course_id)
                data.append({'assignment_id':a['id'], 'assignment_name':a['name']})
                app.logger.debug('New Assignment: %s', assignment)
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
        obj['outcomes'] = []
        obj['student_id'] = student_id

        # Request all outcome rollups from Canvas
        rollups = course.get_outcome_result_rollups(
            user_ids=student_id, aggregate="course", aggregate_stat="mean", outcome_ids=outcome_ids)

        # Limit to scores only
        raw_data = rollups['rollups'][0]['scores']

        app.logger.debug(raw_data)

        # Run through each Outcome
        for outcome in raw_data:
            outcome_id = int(outcome['links']['outcome'])
            outcome_score = outcome['score']

            app.logger.debug(outcome_id)

            # Find the matched assignment in the database
            query = Assignment.query.filter_by(outcome_id=outcome_id).first()

            if query is not None:
                app.logger.debug(query.id)

                assignment_id = query.id

                # Get the assignment and submissions for the student
                assignment = course.get_assignment(assignment_id)
                submission = assignment.get_submission(student_id)

                app.logger.debug('Submission for %s: %s', assignment_id, submission.score)

                # Instantiate an object for the current Outcome/Assignment pair
                item = {'outcome_id': outcome_id,
                        'outcome_score': outcome_score, 'assignment_id': assignment_id}

                # Set a None score to 0
                if submission.score is None:
                    submission.score = 0

                # Check the conditions and update the Canvas gradebook
                if outcome['score'] >= 2.80 and submission.score == 0:
                    item['assignment_score'] = 1
                    submission.edit(submission={'posted_grade': 1})
                elif outcome['score'] < 2.80 and submission.score >= 1:
                    item['assignment_score'] = 0
                    submission.edit(submission={'posted_grade': 0})
                elif outcome['score'] < 2.80 and submission.score == 0:
                    item['assignment_score'] = 0
                    submission.edit(submission={'posted_grade': 0})
                else:
                    item['assignment_score'] = submission.score

                # Store the item in the return object array
                obj['outcomes'].append(item)
            else:
                pass

        return obj

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
        # Start a pool to speed up the requests
        pool = mp.Pool(mp.cpu_count())

        course = canvas.get_course(course_id)

        # define args for the processing function
        items = partial(cls.process_submissions, course=course, outcome_ids=outcome_ids)

        # Post the list to the process function, wait for the results
        result = pool.map(items, student_ids)

        return result
    
    @classmethod
    def get_student_rollups(cls, canvas, course_id, student_id):
        
        course = canvas.get_course(course_id)
        
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

        if 'section_id' in kwargs:
            course = course.get_section(kwargs.get('section_id'))

        # app.logger.debug('Requested course: %s', course_id)

        # Find assignments which are aligned to Outcomes
        query = Assignment.query.filter(Assignment.course_id == course_id, Assignment.outcome_id != None)

        if query.all():

            # Loop Item queries
            for item in query:
                # Store the Query objects as dictionaries in a list
                outcome_list.append(item.__dict__)
                # Store assignment IDs to pass to Canvas
                assignment_list.append(item.id)

            # app.logger.debug('Assignments: %s', assignment_list)
            # app.logger.debug('Outcomes: %s', outcome_list)

            # get active students to request submissions for
            enrollments = course.get_enrollments(role='StudentEnrollment', state='active')
            for e in enrollments:
                item = json.loads(e.to_json())
                student_list.append(item['user']['id'])

            # app.logger.debug('Requested student list: %s', student_list)

            # Request the submissions from Canvas sorted by user
            submissions = course.get_multiple_submissions( 
                assignment_ids=assignment_list, student_ids=student_list, include=('user', 'assignment'), grouped=True)

            # Process the Submissions into usable JSON objects
            for submission_group in submissions:

                submissions = []
                
                for sub in submission_group.submissions:
                    
                    item = json.loads(sub.to_json())

                    # app.logger.debug('Processing %s', item['user']['name'])

                    # app.logger.debug(pprint.pprint(item['user']))

                    if item['user']['id'] in student_list:
                        app.logger.debug('Found ' + item['user']['name'] + ' in the list.')
                        canvas_id = item['user']['id']
                        sis_id = item['user']['login_id']
                        user_name = item['user']['name']

                        assignment_score = item['grade']
                        assignment_id = item['assignment_id']
                        assignment_name = item['assignment']['name']

                        # Get the outcome ID if it matches the assignment ID
                        outcome_id = [int(val['outcome_id']) for val in outcome_list if val['id'] == assignment_id]

                        # app.logger.debug('Appending submissions for %s', item['user']['name'])
                        submission = {
                            'assignment_id': assignment_id,
                            'assignment_name': assignment_name,
                            'assignment_score': assignment_score,
                            'outcome_id': int(outcome_id[0]),
                        }
                        submissions.append(submission)
                
                # app.logger.debug(pprint.pprint(submissions))
                    else:
                        # app.logger.debug('%s is not in the student list', item['user']['name'])
                        # Continue to the next student if the ID isn't present in the current list
                        continue

                # app.logger.debug('Storing completed object for %s', item['user']['name'])
                json_data.append({
                    'canvas_id': canvas_id,
                    'sis_id': sis_id,
                    'user_name': user_name,
                    'submissions': submissions,
                })

        else:
            return None
        
        # app.logger.debug(pprint.pprint(json_data))
        return json_data

    @staticmethod
    def get_rubric_result_for_assignment(canvas, course_id, assignment_id):

        course = canvas.get_course(course_id)

        # Get an assignment by ID
        assignment = course.get_assignment(assignment_id)

        # Use the assignment to get a rubric ID for keys/ID
        rubric = assignment.rubric

        # build a list
        columns = []

        for criteria in rubric:
            column = {}
            column['id'] = criteria['id']
            column['name'] = criteria['description']
            column['outcome_id'] = criteria['outcome_id']
            columns.append(column)

        # Get submissions for the assignment to get rubric evals
        submissions = assignment.get_submissions(include='rubric_assessment')

        # Create a list to store all results
        student_results = list()

        for submission in list(submissions):
            # pprint(submission)
            student_result = {}
            student_result['id'] = submission.user_id
            student_result['score'] = submission.score
            if hasattr(submission, 'rubric_assessment'):
                student_result['rubric'] = submission.rubric_assessment
            student_results.append(student_result)

        return student_results
