from canvasapi import Canvas
from requests_oauthlib import OAuth2Session
from app import app
from flask import request, session
import time


class Auth:
        
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
    def refresh_oauth_token(self):
        """ Get the user refresh token for API calls
        :type user: Int
        :param user: Canvas user ID

        :rtype: Str token
        """
        token = self.oauth.fetch_token(
            app.config["OAUTH_CREDENTIALS"]["canvas"]["token_url"],
            grant_type="refresh_token",
            client_id=app.config["OAUTH_CREDENTIALS"]["canvas"]["id"],
            client_secret=app.config["OAUTH_CREDENTIALS"]["canvas"]["secret"],
            refresh_token=user.refresh_token,
        )

        return token

    @classmethod
    def init_canvas(self, token):
        """ Launch a new Canvas object
        :type token: Str
        :param token: OAuth token

        :rtype:
        """
        expire = token["expires_at"]
        app.logger.info("token expires at: %s", expire)
        if time.time() > expire:
            app.logger.info("Requesting a new token from Canvas")
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
        return self.auth_url

    @classmethod
    def get_token(self):
        token = self.oauth.fetch_token(
            app.config["OAUTH_CREDENTIALS"]["canvas"]["token_url"],
            client_secret=app.config["OAUTH_CREDENTIALS"]["canvas"]["secret"],
            authorization_response=request.url,
            state=session["oauth_state"],
            replace_tokens=True,
        )

        return token
