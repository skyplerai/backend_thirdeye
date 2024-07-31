"""
Django settings for thirdeye project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
import datetime
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-#^_vdt36ryy)4-0f8n27p6a9ikvy4^m*=%(y#$-!&lmbbgf6-!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
AUTH_USER_MODEL = 'authentication.User'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders',
    'channels',
    'notifications',
    'authentication',
    'camera',
    
]

CORS_ALLOWED_ORIGINS = [
    'http://54.90.202.192',  # Adjust with your AWS public IP address
    'https://thethirdeye.com',  # Add other domains if needed
]

# If you want to allow credentials (cookies, Authorization headers, etc.), set this:
CORS_ALLOW_CREDENTIALS = True

# Optional: Specify which HTTP methods are allowed for CORS requests (defaults to ['GET', 'OPTIONS', 'HEAD'])
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']

# Optional: Specify which HTTP headers are allowed for CORS requests (defaults to all headers)
CORS_ALLOW_HEADERS = ['Authorization', 'Content-Type']

# Optional: Set the CORS Expose Headers (defaults to None)
CORS_EXPOSE_HEADERS = []

# Optional: Set the CORS Max-Age (defaults to 86400 seconds)
CORS_MAX_AGE = 86400

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

GOOGLE_CLIENT_ID = '48362687558-b7qotc3aea0ne3irtbne2tp2kkghk6it.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET='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'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    
]
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'authentication.backends.EmailBackend',
    'authentication.backends.GoogleBackend',
]

ROOT_URLCONF = 'thirdeye.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}


SIMPLE_JWT = {
   'ACCESS_TOKEN_LIFETIME': datetime.timedelta(days=365),  
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=365),
}

ASGI_APPLICATION = 'thirdeye.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
WSGI_APPLICATION = 'thirdeye.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'THETHIRDEYE',         # The name of your database
        'USER': 'Kishor',     # Your database username
        'PASSWORD': '#Root782qwerty', # Your database password
        'HOST': 'ec2-13-201-59-248.ap-south-1.compute.amazonaws.com',     # The endpoint of your RDS instance
        'PORT': '3306',                 # The port on which MySQL is running
    }
}
# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'naveenmaga5@gmail.com'
EMAIL_HOST_PASSWORD = 'uyae aysx qssl nisw'

USE_TZ = True
TIME_ZONE = 'UTC'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'camera': {  # Add a logger for your camera app
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
