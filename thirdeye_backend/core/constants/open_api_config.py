from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from thirdeye_backend.core.constants.servers import servers
from thirdeye_backend.settings import app_settings

open_api_config = OpenAPIConfig(
	title=app_settings.APP_NAME,
	version=app_settings.VERSION,
	description="API for ThirdEye",
	servers=servers,
	render_plugins=[
		ScalarRenderPlugin(),
	],
)
