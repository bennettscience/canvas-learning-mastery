from app import db
from app.models import Outcome
from sqlalchemy.orm.session import make_transient

outcomes = Outcome.query.all()

for outcome in outcomes:
    db.session.expunge(outcome)
    make_transient(outcome)

    outcome.outcome_id = outcome.id 
    outcome.id = None

    db.session.add(outcome)

db.session.commit()
