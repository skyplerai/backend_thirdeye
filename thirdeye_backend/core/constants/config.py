import secrets

from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from thirdeye_backend.settings import app_settings

cors_config: CORSConfig = CORSConfig(
	allow_origins=app_settings.ALLOWED_HOSTS,
	allow_methods=["*"],
	allow_credentials=True,
)

csrf_config: CSRFConfig = CSRFConfig(
	secret=secrets.token_urlsafe(32),
	cookie_name="csrftoken",
	cookie_path="/",
	header_name="X-CSRF-Token",
	cookie_secure=True,
	cookie_httponly=True,
	cookie_samesite="lax",
	cookie_domain=None,
	safe_methods={"GET", "HEAD", "OPTIONS"},
	exclude=["/api/webhook", "/api/external"],
	exclude_from_csrf_key="exclude_from_csrf",
)
