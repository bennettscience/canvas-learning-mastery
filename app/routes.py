import time
from flask import json, jsonify, redirect, render_template, request, session, url_for
from flask_login import login_required
from requests_oauthlib import OAuth2Session
from app.models import Outcome, Assignment, User
from app.forms import StoreOutcomesForm
from app.assignments import Assignments
from app.outcomes import Outcomes
from app.courses import Course
from app.auth import Auth
from flask_login import current_user, login_user, logout_user
from canvasapi import Canvas, exceptions
from app import app, db


@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
def index():
    """ App entrance.
    If user is logged in, load the dashboard. Otherwise, load the login screen
    """

    if not current_user.is_anonymous and session["_fresh"]:
        expire = session["oauth_token"]["expires_at"]

        if time.time() > expire:
            # get a new access token and store it
            token = session["oauth_token"]
            client_id = app.config["OAUTH_CREDENTIALS"]["canvas"]["id"]
            refresh_url = app.config["OAUTH_CREDENTIALS"]["canvas"]["token_url"]

            extra = {
                "client_id": client_id,
                "client_secret": app.config["OAUTH_CREDENTIALS"]["canvas"]["secret"],
                "refresh_token": token["refresh_token"],
            }

            oauth_refresh = OAuth2Session(client_id, token=token)
            session["oauth_token"] = oauth_refresh.refresh_token(refresh_url, **extra)
        return redirect(url_for("dashboard"))
    else:
        session.clear()
        logout_user()
        return render_template("login.html", title="Canvas Mastery Doctor")


@app.route("/login", methods=["GET"])
def login():
    """ Log in to the app via OAuth through Canvas
    :methods: GET
    :responses:
        200:
            description: Route to callback for final authentication
        400:
            description: Bad request.
    """
    authorization_url, state = Auth.login()
    session["oauth_state"] = state

    return redirect(authorization_url)


@app.route("/logout", methods=["GET"])
def logout():
    """ Log the current user out."""
    session.clear()
    logout_user()

    return redirect(url_for("index"))


@app.route("/callback", methods=["GET"])
def callback():
    """ Perform final authorization of the user
    :methods: GET
    :responses:
        200:
            description: Successful authentication
        400:
            description: Bad request
    """

    token = Auth.get_token()

    session["oauth_token"] = token

    user_id = str(session["oauth_token"]["user"]["id"])
    user_name = session["oauth_token"]["user"]["name"]

    # Query the DB for an existing user
    user = User.query.filter_by(canvas_id=user_id).first()

    if user:
        # Update the user token
        if user.token != session["oauth_token"]["access_token"]:
            user.token = session["oauth_token"]["access_token"]
            db.session.commit()
    else:
        # User doesn't exist, create a new one
        user = User(
            canvas_id=user_id,
            name=user_name,
            token=session["oauth_token"]["access_token"],
            expiration=session["oauth_token"]["expires_at"],
            refresh_token=session["oauth_token"]["refresh_token"],
        )
        db.session.add(user)
        db.session.commit()

    login_user(user, True)

    return redirect(url_for("dashboard"))


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """ Display the logged-in user's courses. """
    canvas = Auth.init_canvas(session["oauth_token"])
    user = canvas.get_current_user()

    all_courses = user.get_courses(
        state=["available"],
        enrollment_state=["active"],
        enrollment_type="teacher",
        include="total_students",
    )

    courses = []
    for c in all_courses:
        courses.append(Course.process_course(c))

    courses = sorted(courses, key=lambda course: course["term"], reverse=True)

    return render_template("dashboard.html", title="Dashboard", courses=courses), 200


@app.route("/course/<course_id>", methods=["GET"])
@login_required
def course(course_id):
    """ Single course view
    :param course_id: Canvas course ID
    :type course_id: Int

    :methods: GET

    :rtype:
    """
    # Instantiate a new Canvas object
    canvas = Auth.init_canvas(session["oauth_token"])

    # Get the assignment groups from Canvas
    course = canvas.get_course(course_id)
    sections = course.get_sections()

    query = course.get_assignment_groups()
    assignment_groups = [(str(a.id), a.name) for a in query]

    # Populate assignment_group_ids into the Outcomes fetch form dynamically
    form = StoreOutcomesForm(request.values, id=course_id)
    form.assignment_groups.choices = assignment_groups

    # Look only in the current course
    assignments = Assignment.query.filter_by(course_id=course_id)

    if not assignments:
        assignments = []

    # Look up any existing Outcomes by course ID
    outcomes = Outcome.query.filter(Outcome.course_id == course_id)

    if not outcomes:
        outcomes = None

    return render_template(
        "course.html",
        title="Canvas course",
        outcomes=outcomes,
        assignments=assignments,
        sections=sections,
        form=form,
    )


@app.route("/section", methods=["POST"])
def section():
    """ Show single section. """
    data = request.json

    canvas = Auth.init_canvas(session["oauth_token"])

    # Look only in the current course
    assignments = Assignment.query.filter_by(course_id=data["course_id"]).all()

    if not assignments:
        assignments = []
        scores = []
    else:
        try:
            scores = Assignments.get_all_assignment_scores(
                canvas, data["course_id"], section_id=data["section_id"]
            )
        except Exception as e:
            return (
                jsonify(message=f"{e}"),
                500,
            )

    # Sort the scores array by student last name before returning
    if scores is not None:
        scores = sorted(scores, key=lambda x: x["user_name"].split(" "))
    else:
        return (
            jsonify(message="Please import assignments in the 'Alignments' tab."),
            500,
        )

    return jsonify(scores)


@app.route("/course/<course_id>/assignments", methods=["GET"])
def get_course_assignments(course_id):

    canvas = Auth.init_canvas(session["oauth_token"])

    data = Assignments.get_course_assignments(canvas, course_id)

    return jsonify({"success": data})


@app.route("/course/<course_id>/assignments/<assignment_id>/rubric", methods=["GET"])
def get_assignment_rubric(course_id, assignment_id):
    canvas = Auth.init_canvas(session["oauth_token"])

    data = Assignments.build_assignment_rubric_results(canvas, course_id, assignment_id)

    return jsonify({"success": data})


@app.route("/save", methods=["POST"])
def save_outcomes():
    """ Save Outcomes from the course into the database
    :methods: POST

    :rtype:
    """
    # Get the data from the form submission
    data = request.values

    # Instantiate a new Canvas object
    canvas = Auth.init_canvas(session["oauth_token"])

    # Store the course Outcomes
    Outcomes.save_outcome_data(canvas, data["id"])
    Assignments.save_assignment_data(canvas, data["id"], data["assignment_groups"])

    # Reload the page
    return redirect(url_for("course", course_id=data["id"]))


@app.route("/align", methods=["POST"])
def align_assignment_to_outcome():
    """ Align an Assignment to an Outcome
    :methods: POST
    """
    data = request.json

    try:
        Outcomes.align_assignment_to_outcome(
            data["course_id"], data["outcome_id"], data["assignment_id"]
        )
        return jsonify({"success": [data["outcome_id"], data["assignment_id"]]})
    except Exception as e:
        print(f'Received an error {e}')
        return e, 400


@app.route("/sync", methods=["POST"])
def sync_outcome_scores():
    """ Get the Outcomes for the students. """
    # Instantiate a Canvas object
    canvas = Auth.init_canvas(session["oauth_token"])

    json = request.json

    # Send the outcome_list in prep for querying a smaller set
    data = Outcomes.update_student_scores(
        canvas, json["course_id"], json["student_id_list"], json["outcome_id_list"]
    )

    return jsonify({"success": data})


@app.route("/student", methods=["GET"])
def student():
    canvas = Canvas(
        app.config["OAUTH_CREDENTIALS"]["canvas"]["base_url"],
        app.config["API"]["canvas"]["token"],
    )

    data = request.args

    try:
        rollups = Outcomes.get_student_rollups(
            canvas, data.get("course_id"), data.get("student_id")
        )
        return jsonify(rollups)
    except exceptions.BadRequest as e:
        app.logger.debug(e)
        return json.dumps({"success": False}), 400, {"Content-Type": "application/json"}
        # raise BadRequest('Outcomes cannot be requested for teachers', 400, payload=e)


@app.route("/rubric/<section_id>/<assignment_id>", methods=["GET"])
def rubric(section_id, assignment_id):
    return {"msg": f"Received {section_id} and {assignment_id}"}


@app.errorhandler(500)
def internal_error(exception):
    app.logger.error(exception)
    return render_template("500.html"), 500
