from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud
from .. import schemas


router = APIRouter(
    prefix="/api/news",
    tags=["News"]
)


@router.get(
    "/",
    response_model=list[schemas.NewsResponse]
)
def get_news(db: Session = Depends(get_db)):
    return crud.get_news(db)


@router.get(
    "/{news_id}",
    response_model=schemas.NewsResponse
)
def get_news_by_id(
    news_id: int,
    db: Session = Depends(get_db)
):
    news = crud.get_news_by_id(db, news_id)

    if not news:
        raise HTTPException(
            status_code=404,
            detail="News tidak ditemukan"
        )

    return news


@router.post(
    "/",
    response_model=schemas.NewsResponse,
    status_code=201
)
def create_news(
    news: schemas.NewsCreate,
    db: Session = Depends(get_db)
):
    return crud.create_news(db, news)


@router.put(
    "/{news_id}",
    response_model=schemas.NewsResponse
)
def update_news(
    news_id: int,
    news: schemas.NewsUpdate,
    db: Session = Depends(get_db)
):
    updated_news = crud.update_news(
        db,
        news_id,
        news
    )

    if not updated_news:
        raise HTTPException(
            status_code=404,
            detail="News tidak ditemukan"
        )

    return updated_news


@router.delete("/{news_id}")
def delete_news(
    news_id: int,
    db: Session = Depends(get_db)
):
    deleted_news = crud.delete_news(
        db,
        news_id
    )

    if not deleted_news:
        raise HTTPException(
            status_code=404,
            detail="News tidak ditemukan"
        )

    return {
        "message": "News berhasil dihapus",
        "id": news_id
    }

