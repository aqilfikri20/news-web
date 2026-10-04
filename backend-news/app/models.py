from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(30))
    address = Column(Text)
    role = Column(String(20), default="writer", server_default="writer", nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    news = relationship("News", back_populates="author")


class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"

    id = Column(String(36), primary_key=True)
    answer_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Integer, default=0, nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    news = relationship("News", back_populates="category")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    image_url = Column(Text)

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False
    )

    author_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    category = relationship(
        "Category",
        back_populates="news"
    )

    author = relationship(
        "User",
        back_populates="news"
    )
