import json, requests
from app import app, db
from app.models import Outcome, Assignment, User
from app.server import Outcomes, Assignments

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Outcomes': Outcomes,
        'Assignments': Assignments,
        'Outcome': Outcome,
        'Assignment': Assignment,
        'User': User,
        'json': json,
        'requests': requests
    }
