import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'some-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_RECORD_QUERIES = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMINS = ['you@email.com']
    DEBUG_TB_PROFILER_ENABLED = True
    OAUTH_CREDENTIALS = {
        'canvas': {
            'id': 'your_app_id',
            'secret': 'your_app_secret',
            'base_url': 'https://canvas.instructure.com/api/v1/',
            'token_url': 'https://canvas.instructure.com/login/oauth2/token',
            'authorization_url': 'https://canvas.instructure.com/login/oauth2/auth',
            'redirect_url': 'http://localhost:5000/callback',
        }
    }
    DEBUG_TB_INTERCEPT_REDIRECTS = False
