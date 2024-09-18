#authentication/utils.py
import random
import string
from datetime import timedelta
from django.core.mail import EmailMessage
from django.utils import timezone
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from .models import User

def google_authenticate(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
        if 'email' not in idinfo:
            return None

        email = idinfo['email']
        google_id = idinfo['sub']

        # Check if the email is already associated with a regular account
        if User.objects.filter(email=email).exists() and not User.objects.filter(email=email, google_id=google_id).exists():
            return 'existing_email'

        user, created = User.objects.get_or_create(email=email, google_id=google_id)
        if created:
            user.username = email.split('@')[0]
            user.save()

        return user
    except ValueError:
        return None


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def is_otp_valid(user, otp):
    if user.otp != otp:
        return False
    expiration_time = user.otp_created_at + timedelta(minutes=10)
    return timezone.now() <= expiration_time

class Util:
    @staticmethod
    def send_email(data):
        email = EmailMessage(subject=data['email_subject'], body=data['email_body'], to=[data['to_email']])
        email.send()
