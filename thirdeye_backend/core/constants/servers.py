from litestar.openapi.spec import Server

servers: list[Server] = [
	Server(
		url="http://0.0.0.0:8000",
		description="Development server",
	),
	Server(
		url="https://api.thirdeye.com",
		description="Production server",
	),
]
