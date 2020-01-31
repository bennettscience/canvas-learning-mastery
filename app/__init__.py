import os
import logging
from logging.handlers import RotatingFileHandler
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_bootstrap import Bootstrap
from flask_cors import CORS

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config.from_object(Config)
app.config['CORS_HEADERS'] = 'Content-Type'
# app.logger.addHandler(file_handler)
db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = 'index'
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)
CORS(app, resources={r"/student*": {"origins": "https://elkhart.instructure.com/*"}})

from app import app, routes, errors

# Connect to Sentry
# sentry_sdk.init(
#     dsn=app.config['SENTRY_DSN'],
#     integrations=[FlaskIntegration()],
#     send_default_pii=True,
#     release="canvas-mastery@0.2"
# )
