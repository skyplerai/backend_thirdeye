class EnvError(Exception):
	"""Exception raised for errors in the environment.

	Attributes:
		message -- explanation of the error
	"""

	def __init__(self, message: str) -> None:
		self.message = message
		super().__init__(self.message)

	def __str__(self) -> str:
		return self.message
