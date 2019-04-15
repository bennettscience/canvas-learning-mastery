import os
import logging.handlers
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Init logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = logging.handlers.RotatingFileHandler('logs/canvasdoc.log', mode='a', maxBytes=10240, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object(Config)
app.logger.addHandler(file_handler)
db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = 'index'
migrate = Migrate(app, db)
toolbar = DebugToolbarExtension(app)

from app import routes, models

# if not app.debug:
    # if app.config['MAIL_SERVER']:
    #     auth = None
    #     if app.config['MAIL_SERVER'] or app.config['MAIL_PASSWORD']:
    #         auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
    #     secure = None
    #     if app.config['MAIL_USE_TLS']:
    #         secure = ()
    #     mail_handler = SMTPHandler(
    #         mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
    #         fromaddr='no-reply@' + app.config['MAIL_SERVER'],
    #         toaddrs=app.config['ADMINS'],subject='CanvasDoc Failure',
    #         credentials=auth, secure=secure)
    #     mail_handler.setLevel(logging.ERROR)
    #     app.logger.addHandler(mail_handler)
    