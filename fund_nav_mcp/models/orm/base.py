__all__ = ["Base"]

from sqlalchemy import Integer, DateTime, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    """基础模型类"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
