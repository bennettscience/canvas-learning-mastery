from canvasapi import Canvas
from requests_oauthlib import OAuth2Session
from app import app
from flask import request, session
import time


class Auth:
    """ 
    Class to manage the OAuth2 flow for Canvas. 
    Initialize for the user and pass all calls through
    the authorized object.
    """

    def init_canvas(self):
        """ Launch a new Canvas object
        :type token: Str
        :param token: OAuth token

        :returns canvas: Canvas instance
        :rtype: Object
        """
        expire = self.token["expires_at"]

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

        return Canvas(
            app.config["OAUTH_CREDENTIALS"]["canvas"]["base_url"], session["oauth_token"]["access_token"]
        )

    def login(self):
        """Log the user in."""
        return self.auth_url

    def get_token(self):
        """ Retrieve an access token from Canvas. """
        token = self.oauth.fetch_token(
            app.config["OAUTH_CREDENTIALS"]["canvas"]["token_url"],
            client_secret=app.config["OAUTH_CREDENTIALS"]["canvas"]["secret"],
            authorization_response=request.url,
            state=session["oauth_state"],
            replace_tokens=True,
        )

        #  Refactor later into standalone class to manage authorization
        # self.token = token
        return token
