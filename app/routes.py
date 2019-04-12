import requests
from flask import flash, json, jsonify, redirect, render_template, request, session, url_for
from requests_oauthlib import OAuth2Session
from app import app, db
from app.models import Outcome, Assignment, User
from app.forms import StoreOutcomesForm
from app.server import Outcomes, Assignments
from flask_login import current_user, login_user, logout_user
from canvasapi import Canvas

oauth = OAuth2Session(app.config['OAUTH_CREDENTIALS']['canvas']['id'],
                      redirect_uri=app.config['OAUTH_CREDENTIALS']['canvas']['redirect_url'])

def init_canvas(token):
    canvas = Canvas('https://elkhart.beta.instructure.com', token)
    return canvas

def refresh_oauth_token(user):
    token = oauth.fetch_token(app.config['OAUTH_CREDENTIALS']['canvas']['token_url'], \
        grant_type='refresh_token',
        client_id=app.config['OAUTH_CREDENTIALS']['canvas']['id'],
        client_secret=app.config['OAUTH_CREDENTIALS']['canvas']['secret'],
        refresh_token=user.refresh_token)

    return token

@app.route('/')
@app.route('/index')
def index():
    app.logger.info('Index loaded')
    if not current_user.is_anonymous:
        app.logger.info('Current user: %s', current_user.canvas_id)
        return redirect(url_for('user', user_id=current_user.canvas_id))
    # if current_user:
    #     if current_user.expiration < 
    #     return redirect(url_for('user', user_id=current_user.canvas_id))
    return render_template('login.html', title='Canvas Mastery Doctor')

@app.route('/logout')
def logout():
    # Delete the user key from Canvas
    # The canvasapi module doesn't have an endpoint, so we need
    # to build one with requests
    # DELETE /login/oauth2/token
    # https://canvas.instructure.com/doc/api/file.oauth_endpoints.html#post-login-oauth2-token
    headers = {
        'Authorization': 'access_token ' + session['oauth_token']['access_token']
    }

    r = requests.delete(app.config['OAUTH_CREDENTIALS']['canvas']['token_url'], headers=headers)
    app.logger.info(r.json())

    app.logger.info('Clearing session')
    session.clear()
    logout_user()

    # Finally return the user to the index
    return redirect(url_for('index'))

@app.route('/login')
def login():
    app.logger.info('Launching oauth flow')
    authorization_url, state = oauth.authorization_url(app.config['OAUTH_CREDENTIALS']['canvas']['authorization_url'])

    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    app.logger.info('Received token, validating with Canvas')
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
    user = User.query.filter_by(canvas_id=user_id).first()

    if user:
        app.logger.info('User: %s', user)
        if user.token != session['oauth_token']['access_token']:
            user.token = session['oauth_token']['access_token']
            db.session.commit()
    else:
        app.logger.info('Creating new user in db')
        user = User(canvas_id=user_id, 
                    name=user_name, 
                    token=session['oauth_token']['access_token'],
                    expiration=session['oauth_token']['expires_at'],
                    refresh_token=session['oauth_token']['refresh_token'])
        db.session.add(user)
        db.session.commit()
    login_user(user, True)

    return redirect(url_for('user', user_id=user_id))

@app.route('/user/<user_id>')
def user(user_id):
    app.logger.info('Access token: %s', session['oauth_token'])
    canvas = init_canvas(session['oauth_token']['access_token'])

    app.logger.info('Requesting the user id from acanvas')
    app.logger.info('The current user is %s', current_user)
    user = current_user
    app.logger.info('The Canvas user is %s', user.canvas_id)

    courses = canvas.get_courses(state=['available'])

    return render_template('user.html', title='User', user=user, courses=courses)

@app.route('/course/<course_id>', methods=['GET', 'POST'])
def course(course_id):
    canvas = init_canvas(session['oauth_token']['access_token'])
    form = StoreOutcomesForm(request.values, id=course_id)
    if request.method == 'POST':
        print(form.id.data)
        outcomes = Outcomes.save_course_data(canvas, form.id.data)
        # return redirect(url_for('course/<id>', id))

    outcomes = Outcome.query.all()

    if not outcomes:
        outcomes = None

    assignments = Assignment.query.all()

    if not assignments:
        assignments = None
        scores = None
    else:
        scores = Assignments.get_all_assignment_scores(canvas, course_id)

    return render_template('course.html',
        title='Canvas course',
        outcomes=outcomes,
        scores=scores,
        assignments=assignments,
        form=form
    )

@app.route('/align', methods=['POST'])
def align_items():
    data = request.json
    # print(data)
    assignment = Assignment.query.get(data['assignment_id'])
    assignment.outcome_id = data['outcome_id']
    db.session.commit()
    
    # outcome = Outcome.align(assignment)
    # print('Line 51', post['outcome_id'], post['assignment_id'])
    return jsonify({'success': [data['outcome_id'], data['assignment_id']]})

@app.route('/outcomes', methods=['POST'])
def get_user_outcomes():
    canvas = init_canvas(session['oauth_token']['access_token'])
    print("{}".format(request.json))
    json = request.json
    data = Outcomes.get_user_outcomes(canvas, json['course_id'], json['student_id_list'])
    return jsonify({'success': data})
