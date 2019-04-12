from app import app, db, login
from flask_login import UserMixin

alignments = db.Table('alignments',
    db.Column('outcome_id', db.Integer, db.ForeignKey('outcome.id')),
    db.Column('assignment_id', db.Integer, db.ForeignKey('assignment.id'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    canvas_id = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String, nullable=False)
    expiration = db.Column(db.Integer)
    refresh_token = db.Column(db.String)

    def __repr__(self):
        return 'User: {} | {} | {} | {} | {} | {}'.format(self.id, self.canvas_id, self.name, self.token, self.expiration, self.refresh_token)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Outcome(db.Model):
    """ Outcome object for the database.
      id    - unique int
      title - string name
      score - binary 0 or 1
      """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    score = db.Column(db.Integer)

    def align(self, assignment):
    
        """ Description
        :type self:
        :param self:
    
        :type assignment:
        :param assignment:
    
        :raises:
    
        :rtype:
        """    
        if not self.is_aligned(assignment):
            self.assignment.remove(self.assignment[0])
            self.assignment.append(assignment)
            db.session.commit()
            return 'Updated alignment to {}'.format(assignment.title)
        else:
            return '{} is already aligned!'.format(assignment.title)

    # Check that it isn't aleady aligned to the Assignment
    def is_aligned(self, assignment):
    
        """ Description
        :type self:
        :param self:
    
        :type assignment:
        :param assignment:
    
        :raises:
    
        :rtype:
        """    
        return assignment.outcome_id == self.id

    def __repr__(self):
        return '< {} || {} >'.format(self.title, self.id)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    score = db.Column(db.Integer)
    # Link to the outcome ID
    outcome_id = db.Column(db.Integer, db.ForeignKey('outcome.id'))

    outcome = db.relationship('Outcome', backref='assignment', passive_updates=False, uselist=False)

    def __repr__(self):
        return '< {} || {} || {}>'.format(self.id, self.title, self.outcome_id)
