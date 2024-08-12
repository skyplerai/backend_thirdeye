from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class BaseModel(DeclarativeBase):
	pass


class Base:
	@declared_attr  # type: ignore
	def __tablename__(cls) -> str:  # type: ignore # noqa
		return cls.__name__.lower()  # type: ignore

	id: Mapped[int] = mapped_column(primary_key=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
