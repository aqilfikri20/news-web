from sqlalchemy.orm import Session, joinedload

from . import models
from . import schemas


def create_user(
    db: Session,
    user: schemas.UserCreate
):
    db_user = models.User(
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def get_users(
    db: Session
):
    return db.query(models.User).all()


def get_user_by_id(
    db: Session,
    user_id: int
):
    return db.query(models.User).filter(
        models.User.id == user_id
    ).first()


def get_user_by_email(
    db: Session,
    email: str
):
    return db.query(models.User).filter(
        models.User.email == email
    ).first()


def update_user(
    db: Session,
    user_id: int,
    user: schemas.UserUpdate
):
    db_user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not db_user:
        return None

    update_data = user.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    return db_user


def delete_user(
    db: Session,
    user_id: int
):
    db_user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not db_user:
        return None

    db.delete(db_user)
    db.commit()

    return db_user


# =========================================================
# CATEGORY CRUD
# =========================================================


def create_category(
    db: Session,
    category: schemas.CategoryCreate
):
    db_category = models.Category(
        name=category.name
    )

    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    return db_category


def get_categories(
    db: Session
):
    return db.query(models.Category).all()


def get_category_by_id(
    db: Session,
    category_id: int
):
    return db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()


def update_category(
    db: Session,
    category_id: int,
    category: schemas.CategoryUpdate
):
    db_category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not db_category:
        return None

    update_data = category.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)

    return db_category


def delete_category(
    db: Session,
    category_id: int
):
    db_category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not db_category:
        return None

    db.delete(db_category)
    db.commit()

    return db_category


# =========================================================
# NEWS CRUD
# =========================================================


def create_news(
    db: Session,
    news: schemas.NewsCreate
):
    db_news = models.News(
        title=news.title,
        description=news.description,
        content=news.content,
        image_url=news.image_url,
        category_id=news.category_id,
        author_id=news.author_id
    )

    db.add(db_news)
    db.commit()
    db.refresh(db_news)

    return db_news

def get_news(db: Session):
    return (
        db.query(models.News)
        .options(
            joinedload(models.News.category),
            joinedload(models.News.author)
        )
        .all()
    )


def get_news_by_id(db: Session, news_id: int):
    return (
        db.query(models.News)
        .options(
            joinedload(models.News.category),
            joinedload(models.News.author)
        )
        .filter(models.News.id == news_id)
        .first()
    )


def update_news(
    db: Session,
    news_id: int,
    news: schemas.NewsUpdate
):
    db_news = db.query(models.News).filter(
        models.News.id == news_id
    ).first()

    if not db_news:
        return None

    update_data = news.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(db_news, key, value)

    db.commit()
    db.refresh(db_news)

    return db_news


def delete_news(
    db: Session,
    news_id: int
):
    db_news = db.query(models.News).filter(
        models.News.id == news_id
    ).first()

    if not db_news:
        return None

    db.delete(db_news)
    db.commit()

    return db_news
