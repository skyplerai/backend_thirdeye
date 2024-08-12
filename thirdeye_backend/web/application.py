from litestar import Litestar
from litestar_granian import GranianPlugin
from thirdeye_backend.core import Constants, configure_logging
from thirdeye_backend.settings import app_settings


def construct_app() -> Litestar:
	app = Litestar(
		debug=app_settings.DEBUG,
		response_headers=Constants.RESPONSE_HEADERS,
		allowed_hosts=app_settings.ALLOWED_HOSTS,
		cors_config=Constants.CORS_CONFIG,
		csrf_config=Constants.CSRF_CONFIG,
		openapi_config=Constants.OPEN_API_CONFIG,
		plugins=[GranianPlugin()],
		route_handlers=[],
	)
	configure_logging()
	return app


third_eye_app: Litestar = construct_app()
