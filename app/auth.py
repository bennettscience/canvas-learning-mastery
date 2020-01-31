from canvasapi import Canvas
from requests_oauthlib import OAuth2Session
from app import app
from flask import request, session
import time


class Auth:
    """ Manage OAuth flow. """
        
    oauth = OAuth2Session(
        app.config["OAUTH_CREDENTIALS"]["canvas"]["id"],
        redirect_uri=app.config["OAUTH_CREDENTIALS"]["canvas"]["redirect_url"],
    )

    auth_url = oauth.authorization_url(
        app.config["OAUTH_CREDENTIALS"]["canvas"]["authorization_url"]
    )

    def __init__(self):
        pass

    @classmethod
    def init_canvas(self, token):
        """ Launch a new Canvas object
        :type token: Str
        :param token: OAuth token

        :returns canvas: Canvas instance
        :rtype: Object
        """
        expire = token["expires_at"]

        if time.time() > expire:
            # get a new access token and store it
            client_id = app.config["OAUTH_CREDENTIALS"]["canvas"]["id"]
            refresh_url = app.config["OAUTH_CREDENTIALS"]["canvas"]["token_url"]

            extra = {
                "client_id": client_id,
                "client_secret": app.config["OAUTH_CREDENTIALS"]["canvas"]["secret"],
                "refresh_token": token["refresh_token"],
            }

            oauth_refresh = OAuth2Session(client_id, token=token)
            session["oauth_token"] = oauth_refresh.refresh_token(refresh_url, **extra)

        canvas = Canvas(
            "https://elkhart.instructure.com", session["oauth_token"]["access_token"]
        )
        return canvas

    @classmethod
    def login(self):
        """Log the user in."""
        return self.auth_url

    @classmethod
    def get_token(self):
        """ Retrieve an access token from Canvas. """
        token = self.oauth.fetch_token(
            app.config["OAUTH_CREDENTIALS"]["canvas"]["token_url"],
            client_secret=app.config["OAUTH_CREDENTIALS"]["canvas"]["secret"],
            authorization_response=request.url,
            state=session["oauth_state"],
            replace_tokens=True,
        )

        return token
