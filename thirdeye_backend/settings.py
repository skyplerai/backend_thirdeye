import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from thirdeye_backend.core.errors.env_error import EnvError


class AppSettings:
	def __init__(self) -> None:
		load_dotenv(".env")
		self.APP_NAME: str = os.environ.get("APP_NAME", "MyApp")
		self.VERSION: str = os.environ.get("VERSION", "1.0.0")
		self.HOST: str = os.environ.get("HOST", "0.0.0.0")
		self.PORT: int = int(os.environ.get("PORT", 8000))
		self.DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
		self.SECRET_KEY: str = os.environ.get("SECRET_KEY", "Something")
		self.HASH_ALGORITHM: str = os.environ.get("HASH_FUNCTION", "sha256")
		self.TOKEN_EXPIRATION: int = int(os.environ.get("TOKEN_EXPIRATION", 3600))
		self.REFRESH_TOKEN_EXPIRATION: int = int(os.environ.get("REFRESH_TOKEN_EXPIRATION", 86400))
		self.DATABASE_URI: str = os.environ.get("DATABASE_URI", "mongodb://localhost:27017/thirdeye")
		self.LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
		self.TIMEOUT: int = int(os.environ.get("TIMEOUT", 30))
		self.STATIC_URL: str = os.environ.get("STATIC_URL", "/static/")
		self.ALLOWED_HOSTS: list[str] = os.environ.get("ALLOWED_HOSTS", "").split(",")
		self.WORKERS: int = int(os.environ.get("WORKERS", 1))
		self.THREADS: int = int(os.environ.get("THREADS", 1))

		self.__validate()

	def __validate(self) -> None:
		if not self.SECRET_KEY:
			raise EnvError("SECRET_KEY is required")
		if self.HASH_ALGORITHM not in ["sha256", "sha512"]:
			raise EnvError("HASH_FUNCTION must be either sha256 or sha512")
		if self.TOKEN_EXPIRATION < 1:
			raise EnvError("TOKEN_EXPIRATION must be a positive integer")
		if self.REFRESH_TOKEN_EXPIRATION < 1:
			raise EnvError("REFRESH_TOKEN_EXPIRATION must be a positive integer")
		if not self.DATABASE_URI:
			raise EnvError("DATABASE_URI is required")
		if self.TIMEOUT < 1:
			raise EnvError("TIMEOUT must be a positive integer")

	def __getitem__(self, key: str) -> Any:
		return getattr(self, key)


@lru_cache
def get_app_settings() -> AppSettings:
	return AppSettings()


app_settings: AppSettings = get_app_settings()
