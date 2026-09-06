from pydantic import BaseModel, ConfigDict
from datetime import datetime


# =========================
# USER
# =========================

class UserBase(BaseModel):
    name: str
    email: str
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    role: str | None = None


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# CATEGORY
# =========================

class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None


class CategoryResponse(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# =========================
# NEWS CREATE
# =========================

class NewsBase(BaseModel):
    title: str
    description: str | None = None
    content: str
    image_url: str | None = None
    category_id: int
    author_id: int


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    image_url: str | None = None
    category_id: int | None = None
    author_id: int | None = None



class NewsAuthorResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class NewsResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    content: str
    image_url: str | None = None

    category: CategoryResponse
    author: NewsAuthorResponse

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: str
    password: str