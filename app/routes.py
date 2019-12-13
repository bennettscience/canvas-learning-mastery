import time
from sentry_sdk import last_event_id, configure_scope
from flask import json, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from requests_oauthlib import OAuth2Session
from app.models import Outcome, Assignment, User
from app.forms import StoreOutcomesForm
from app.server import Outcomes, Assignments
from flask_login import current_user, login_user, logout_user
from canvasapi import Canvas, exceptions
from app import app, db, CORS

# Canvas OAuth login
oauth = OAuth2Session(app.config['OAUTH_CREDENTIALS']['canvas']['id'],
                      redirect_uri=app.config['OAUTH_CREDENTIALS']['canvas']['redirect_url'])


def init_canvas(token):
    """ Launch a new Canvas object
    :type token: Str
    :param token: OAuth token

    :rtype:
    """
    expire = token['expires_at']
    app.logger.info('token expires at: %s', expire)
    if time.time() > expire:
        app.logger.info('Requesting a new token from Canvas')
        # get a new access token and store it
        client_id = app.config['OAUTH_CREDENTIALS']['canvas']['id']
        refresh_url = app.config['OAUTH_CREDENTIALS']['canvas']['token_url']

        extra = {
            'client_id': client_id,
            'client_secret': app.config['OAUTH_CREDENTIALS']['canvas']['secret'],
            'refresh_token': token['refresh_token'],
        }

        oauth_refresh = OAuth2Session(client_id, token=token)
        session['oauth_token'] = oauth_refresh.refresh_token(
            refresh_url, **extra)

    canvas = Canvas('https://elkhart.instructure.com',
                    session['oauth_token']['access_token'])
    return canvas


def refresh_oauth_token(user):
    """ Get the user refresh token for API calls
    :type user: Int
    :param user: Canvas user ID

    :rtype: Str token
    """
    token = oauth.fetch_token(app.config['OAUTH_CREDENTIALS']['canvas']['token_url'],
                              grant_type='refresh_token',
                              client_id=app.config['OAUTH_CREDENTIALS']['canvas']['id'],
                              client_secret=app.config['OAUTH_CREDENTIALS']['canvas']['secret'],
                              refresh_token=user.refresh_token)

    return token


@app.route('/refresh')
def refresh():
    token = session['oauth_token']
    client_id = app.config['OAUTH_CREDENTIALS']['canvas']['id']
    refresh_url = app.config['OAUTH_CREDENTIALS']['canvas']['token_url']

    extra = {
        'client_id': client_id,
        'client_secret': app.config['OAUTH_CREDENTIALS']['canvas']['secret'],
        'refresh_token': token['refresh_token'],
    }

    canvas = OAuth2Session(client_id, token=token)
    session['oauth_token'] = canvas.refresh_token(refresh_url, **extra)
    print(time.time())
    return jsonify(session['oauth_token'])


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
# @lti(request='initial', role='any', app=app)
def index():

    app.logger.info('Index loaded')
    if not current_user.is_anonymous and session['_fresh']:
        app.logger.info('Current user: %s', current_user)
        app.logger.info('Session: %s', session)
        expire = session['oauth_token']['expires_at']
        app.logger.info('Token expires at: %s', expire)

        if time.time() > expire:
            app.logger.info('Requesting a new token from Canvas')
            # get a new access token and store it
            token = session['oauth_token']
            client_id = app.config['OAUTH_CREDENTIALS']['canvas']['id']
            refresh_url = app.config['OAUTH_CREDENTIALS']['canvas']['token_url']

            extra = {
                'client_id': client_id,
                'client_secret': app.config['OAUTH_CREDENTIALS']['canvas']['secret'],
                'refresh_token': token['refresh_token'],
            }

            oauth_refresh = OAuth2Session(client_id, token=token)
            session['oauth_token'] = oauth_refresh.refresh_token(
                refresh_url, **extra)
        return redirect(url_for('dashboard'))
    else:
        session.clear()
        logout_user()
        return render_template('login.html', title='Canvas Mastery Doctor')


@app.route('/logout', methods=['GET'])
def logout():
    # Delete the user key from Canvas
    # The canvasapi module doesn't have an endpoint, so we need
    # to build one with requests
    # DELETE /login/oauth2/token
    # https://canvas.instructure.com/doc/api/file.oauth_endpoints.html#post-login-oauth2-token
    # headers = {
    #     'Authorization': 'access_token ' + session['oauth_token']['access_token']
    # }

    # r = requests.delete(app.config['OAUTH_CREDENTIALS']['canvas']['token_url'], headers=headers)
    # app.logger.info(r.json())

    app.logger.info('Clearing session')
    session.clear()
    logout_user()

    # Finally return the user to the index
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """ Log in to the app via OAuth through Canvas
    :methods: GET
    :responses:
        200:
            description: Route to callback for final authentication
        400:
            description: Bad request.
    """
    app.logger.info('Launching oauth flow')
    authorization_url, state = oauth.authorization_url(
        app.config['OAUTH_CREDENTIALS']['canvas']['authorization_url'])

    session['oauth_state'] = state
    return redirect(authorization_url)


@app.route('/callback', methods=['GET'])
def callback():
    """ Perform final authorization of the user
    :methods: GET
    :responses:
        200:
            description: Successful authentication
        400:
            description: Bad request
    """
    app.logger.info('Received token, validating with Canvas,')
    token = oauth.fetch_token(app.config['OAUTH_CREDENTIALS']['canvas']['token_url'],
                              client_secret=app.config['OAUTH_CREDENTIALS']['canvas']['secret'],
                              authorization_response=request.url,
                              state=session['oauth_state'],
                              replace_tokens=True
                              )

    session['oauth_token'] = token

    user_id = str(session['oauth_token']['user']['id'])
    user_name = session['oauth_token']['user']['name']

    app.logger.info('The user is %s with ID %s', user_name, user_id)
    app.logger.info('Querying database for user')

    # Query the DB for an existing user
    user = User.query.filter_by(canvas_id=user_id).first()

    if user:
        app.logger.info('User: %s', user)

        # Update the user token
        if user.token != session['oauth_token']['access_token']:
            user.token = session['oauth_token']['access_token']
            db.session.commit()
    else:
        app.logger.info('Creating new user in db')

        # User doesn't exist, create a new one
        user = User(canvas_id=user_id,
                    name=user_name,
                    token=session['oauth_token']['access_token'],
                    expiration=session['oauth_token']['expires_at'],
                    refresh_token=session['oauth_token']['refresh_token'])
        db.session.add(user)
        db.session.commit()
    login_user(user, True)

    return redirect(url_for('dashboard'))


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """ List the logged-in user's courses
    :methods: GET

    :rtype: List courses
    """
    # Instantiate a new Canvas object
    canvas = init_canvas(session['oauth_token'])

    # Need to specify total students in the API call.
    all_courses = canvas.get_courses(state=['available'], enrollment_state=[
                                     'active'], include='total_students')

    # Instantiate a list to hold pared down course objects for display
    courses = []
    for c in all_courses:
        item = {}
        query = Assignment.query.filter(Assignment.course_id == c.id).filter(
            Assignment.outcome_id != None)

        item['outcomes'] = query.count()
        item['id'] = c.id
        item['name'] = c.name

        courses.append(item)

    app.logger.info('Courses: %s', courses)

    return render_template('dashboard.html', title='Dashboard', courses=courses)


@app.route('/course/<course_id>', methods=['GET'])
def course(course_id):
    """ Single course view
    :type course_id: Int
    :param course_id: Canvas course ID

    :methods: POST

    :rtype:
    """
    app.logger.info('Course requested: %s', course_id)

    # Instantiate a new Canvas object
    canvas = init_canvas(session['oauth_token'])

    # Get the assignment groups from Canvas
    current_course = canvas.get_course(course_id)
    sections = current_course.get_sections()

    query = current_course.get_assignment_groups()

    # Populate assignment_group_ids into the Outcomes fetch form dynamically
    form = StoreOutcomesForm(request.values, id=course_id)
    assignment_groups = [(str(a.id), a.name) for a in query]

    app.logger.debug('Setting form assignment groups to: %s',
                     assignment_groups)
    form.assignment_groups.choices = assignment_groups

    # Look only in the current course
    assignments = Assignment.query.filter_by(course_id=course_id)
    app.logger.info('Assignments: %s', assignments)

    if not assignments:
        app.logger.info('No assingments found for this course')
        assignments = []

    # Look up any existing Outcomes by course ID
    outcomes = Outcome.query.filter(Outcome.course_id == course_id)

    if not outcomes:
        app.logger.debug('No outcomes, returning None')
        outcomes = None

    return render_template('course.html',
                           title='Canvas course',
                           outcomes=outcomes,
                           assignments=assignments,
                           sections=sections,
                           form=form
                           )


@app.route('/section', methods=['POST'])
def section():
    data = request.json

    canvas = init_canvas(session['oauth_token'])

    # Look only in the current course
    assignments = Assignment.query.filter_by(course_id=data['course_id'])
    app.logger.info('Assignments: %s', assignments)

    if not assignments:
        app.logger.info('No assingments found for this course')
        assignments = []
        scores = []
    else:
        try:
            app.logger.info('Found assignments, getting scores')
            scores = Assignments.get_all_assignment_scores(
                canvas, data['course_id'], section_id=data['section_id'])
        except Exception:
            return jsonify(message="You've requested an assignment not available to this section. Please check your item alignments."), 403

    # Sort the scores array by student last name before returning
    if scores is not None:
        scores = sorted(scores, key=lambda x: x['user_name'].split(" "))
    else:
        return jsonify(message="Please import assignments in the 'Alignments' tab."), 500

    return jsonify(scores)
    # return jsonify({"assignments": assignments, "scores": scores})

@app.route('/course/<course_id>/assignments', methods=['GET'])
def get_course_assignments(course_id):
    
    canvas = init_canvas(session['oauth_token'])

    data = Assignments.get_course_assignments(canvas, course_id)
    print(data)

    return jsonify({"success": data})

@app.route('/course/<course_id>/assignments/<assignment_id>/rubric', methods=['GET'])
def get_assignment_rubric(course_id, assignment_id):
    canvas = init_canvas(session['oauth_token'])

    data = Assignments.get_assignment_rubric_results(canvas, course_id, assignment_id)

    return jsonify({"success": data})

@app.route('/save', methods=['POST'])
def save_outcomes():
    """ Save Outcomes from the course into the database
    :methods: POST

    :rtype:
    """
    # Get the data from the form submission
    data = request.values

    # Instantiate a new Canvas object
    canvas = init_canvas(session['oauth_token'])

    app.logger.debug('Course ID: %s, Assignment group ID: %s',
                     data['id'], data['assignment_groups'])

    # Store the course Outcomes
    Outcomes.save_course_data(
        canvas, data['id'], data['assignment_groups'])

    # Reload the page
    return redirect(url_for('course', course_id=data['id']))


@app.route('/align', methods=['POST'])
def align_items():
    """ Align an Assignment to an Outcome
    :methods: POST
    """
    data = request.json

    # Get the Outcome and Assignment specified
    outcome = Outcome.query.filter_by(outcome_id=data['outcome_id']).first()
    assignment = Assignment.query.get(data['assignment_id'])

    # Run the alignment and save
    outcome.align(assignment)
    db.session.commit()
    return jsonify({'success': [data['outcome_id'], data['assignment_id']]})


@app.route('/outcomes', methods=['POST'])
def get_user_outcomes():
    """ Get the Outcomes for the students
    :raises:

    :rtype:
    """
    app.logger.debug('Requested score update.')

    # Instantiate a Canvas object
    canvas = init_canvas(session['oauth_token'])

    json = request.json
    app.logger.debug("Submitted request: %s", json)

    # Send the outcome_list in prep for querying a smaller set
    data = Outcomes.update_student_scores(
        canvas, json['course_id'], json['student_id_list'], json['outcome_id_list'])

    return jsonify({'success': data})

@app.route('/student', methods=['GET'])
def student():
    canvas = Canvas(app.config['OAUTH_CREDENTIALS']['canvas']['base_url'],
                    app.config['API']['canvas']['token'])

    data = request.args

    app.logger.debug(data)

    try:
        rollups = Outcomes.get_student_rollups(
            canvas, data.get('course_id'), data.get('student_id'))
        return jsonify(rollups)
    except exceptions.BadRequest as e:
        app.logger.debug(e)
        return json.dumps({'success': False}), 400, {'Content-Type': 'application/json'}
        # raise BadRequest('Outcomes cannot be requested for teachers', 400, payload=e)

@app.route('/rubric/<section_id>/<assignment_id>', methods=["GET"])
def rubric(section_id, assignment_id):
    return {"msg": f'Received {section_id} and {assignment_id}'}

# @app.errorhandler(500)
# def server_error_handler(error):
#     return render_template("500.html", sentry_event_id=last_event_id()), 500


@app.errorhandler(500)
def internal_error(exception):
    app.logger.error(exception)
    return render_template('500.html'), 500
