from app import app, db, login
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """ User DB Model
        Store the User object for authentication and matching courses

    """
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    canvas_id = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String, nullable=False)
    expiration = db.Column(db.Integer)
    refresh_token = db.Column(db.String)

    def __repr__(self):
        return 'User: {} | {} '.format(self.name, self.canvas_id)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Outcome(db.Model):
    """ Outcome object for the database.
      id : unique int
      title : string name
      score : binary 0 or 1
      courses: list of courses the outcome is assessed in
      """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    score = db.Column(db.Integer)
    course_id = db.Column(db.Integer)
    assignment_id = db.relationship('Assignment', uselist=False, back_populates='outcome')

    def align(self, assignment):
        if self.is_aligned():
            self.assignment.remove(self.assignment[0])
            self.assignment.append(assignment)
            db.session.commit()
            return 'Updated alignment to {}'.format(assignment.title)
        else:
            self.assignment.append(assignment)
            db.session.commit()
            return 'Aligned {}'.format(assignment.title)

    # Check that it isn't aleady aligned to the Assignment
    def is_aligned(self): 
        return self.assignment_id is not None

    def __repr__(self):
        return '< {} || {} || Assignment: {} >'.format(self.title, self.id, self.assignments)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    score = db.Column(db.Integer)
    course_id = db.Column(db.Integer)
    outcome_id = db.Column(db.Integer, db.ForeignKey('outcome.id'))

    outcome = db.relationship('Outcome', backref='assignment', passive_updates=False, uselist=False)

    def __repr__(self):
        return '< {} || {} || {} || {}>'.format(self.id, self.title, self.course_id, self.outcome_id)


# # TODO: Figure out how to actually use an association table
# class OutcomeAssignmentLinks(db.Model):
#     __tablename__ = 'alignments'
#     assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), primary_key=True)
#     outcome_id = db.Column(db.Integer, db.ForeignKey('outcome.id'), primary_key=True)
#     assignment = db.relationship(Assignment, backref="outcome_link", lazy='dynamic')
#     outcome = db.relationship(Outcome, backref="assignment_link", lazy='dynamic')