from app import app, db, login
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """ User Object
        Store the User object for authentication and matching courses
        id : unique int
        canvas_id : Canvas LMS user ID
        name : user name
        token : Canvas OAuth access token
        expiration : Timestamp expiration of the token
        refresh_token : sent if the expiration is past
    """
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    canvas_id = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    expiration = db.Column(db.Integer)
    refresh_token = db.Column(db.String(255))

    def __repr__(self):
        return 'User: {} | {} '.format(self.name, self.canvas_id)

@login.user_loader
def load_user(id):
    return User.query.get(id)


class Outcome(db.Model):
    """ Outcome object
      id : unique int
      title : string name
      outcome_id: matches Canvas outcome ID
      course_id: course aligned with outcome
      assignment_id: relationship to a single assignment
      """
    id = db.Column(db.Integer, primary_key=True)
    outcome_id = db.Column(db.Integer)
    title = db.Column(db.String(64))
    course_id = db.Column(db.Integer)
    assignment_id = db.relationship('Assignment', uselist=False, back_populates='outcome')

    def align(self, assignment):
        if self.is_aligned():

            if(assignment is not None):
                self.assignment.remove(self.assignment[0])
                self.assignment.append(assignment)
                db.session.commit()
                return 'Updated alignment to {}'.format(assignment.title)
            else:
                self.assignment.remove(self.assignment[0])
                db.session.commit()
        else:
            self.assignment.append(assignment)
            db.session.commit()
            return 'Aligned {}'.format(assignment.title)

    # Check that it isn't aleady aligned to the Assignment
    def is_aligned(self): 
        return self.assignment_id is not None

    def __repr__(self):
        return '< {} || {} || Assignment: {} >'.format(self.title, self.id, self.assignment_id)

class Assignment(db.Model):
    """ Assignment object model
        id : Canvas Assignment ID
        title : Canvas Assignment title
        course_id : Parent course for the assignment
        outcome_id : Linked outcome for updating scores
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    course_id = db.Column(db.Integer)
    outcome_id = db.Column(db.Integer, db.ForeignKey('outcome.id'), nullable=True)

    outcome = db.relationship('Outcome', backref='assignment', passive_updates=False, uselist=False)

    def __repr__(self):
        return '< {} || {} || {} || {}>'.format(self.id, self.title, self.course_id, self.outcome_id)
