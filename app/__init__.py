import os
import logging.handlers
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_bootstrap import Bootstrap

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Init logging
if not os.path.exists('tmp/logs'):
    os.mkdir('tmp/logs')
file_handler = logging.handlers.RotatingFileHandler('tmp/logs/canvasdoc.log', mode='a', maxBytes=10240, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.ERROR)

app = Flask(__name__)
app.config.from_object(Config)
app.logger.addHandler(file_handler)
db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = 'index'
migrate = Migrate(app, db)
toolbar = DebugToolbarExtension(app)
bootstrap = Bootstrap(app)

from app import routes, models

# Connect to Sentry
sentry_sdk.init(
    dsn=app.config['SENTRY_DSN'],
    integrations=[FlaskIntegration()],
    release="canvas-mastery@0.1.1"
)
