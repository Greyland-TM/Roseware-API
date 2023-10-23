from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
import os

class WebhookAuthentication(BasicAuthentication):
    def authenticate_credentials(self, userid, password, request=None):
        # Get the environment variables
        http_auth_user = os.environ.get('HTTP_AUTH_USER')
        http_auth_pass = os.environ.get('HTTP_AUTH_PASSWORD')

        if userid == http_auth_user and password == http_auth_pass:
            try:
                user = get_user_model().objects.get(email=userid)
                return (user, None)
            except get_user_model().DoesNotExist:
                raise AuthenticationFailed('Invalid email/password.')
        else:
            raise AuthenticationFailed('Invalid email/password.')
