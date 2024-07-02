import random
import string
from datetime import  timedelta
from django.core.mail import EmailMessage
from django.utils import timezone  # Import timezone for aware datetime handling
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from .models import User

def google_authenticate(token):
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        google_user_id = idinfo['sub']
        email = idinfo['email']
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')
        
        # Check if user already exists
        user, created = User.objects.get_or_create(email=email, defaults={
            'username': email.split('@')[0],
            'is_verified': True,
            'is_active': True
        })
        
        return user
    except ValueError:
        # Invalid token
        return None


def generate_otp():
    """Generate a random 6-digit OTP."""
    return ''.join(random.choices(string.digits, k=6))

def is_otp_valid(user):
    """
    Check if the OTP for the user is valid.
    OTP is valid if it exists, has been created within the last 5 minutes.
    """
    if user.otp and user.otp_created_at:
        expiry_time = user.otp_created_at + timedelta(minutes=5)
        return timezone.now() <= expiry_time  # Compare with timezone-aware current time
    return False

class Util:
    @staticmethod
    def send_email(data):
        """
        Send an email using Django's EmailMessage class.
        Requires 'email_subject', 'email_body', and 'to_email' keys in data dictionary.
        """
        email = EmailMessage(
            subject=data['email_subject'],
            body=data['email_body'],
            to=[data['to_email']]
        )
        email.send()
