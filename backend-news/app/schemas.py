from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str
    phone: str | None = None
    address: str | None = None
    role: str = "writer"

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    phone: str = Field(min_length=1, max_length=30)
    address: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_answer: str = Field(min_length=1, max_length=12)

    model_config = ConfigDict(extra="ignore")

class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    password: str | None = None

class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: str | None = None

class CategoryResponse(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class NewsBase(BaseModel):
    title: str
    description: str | None = None
    content: str
    image_url: str | None = None
    category_id: int


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    image_url: str | None = None
    category_id: int | None = None

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


class NewsPageResponse(BaseModel):
    items: list[NewsResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_answer: str = Field(min_length=1, max_length=12)


class WriterProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    phone: str = Field(min_length=1, max_length=30)
    address: str = Field(min_length=1)
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str | None = Field(default=None, max_length=128)
    confirm_password: str | None = Field(default=None, max_length=128)
