from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..cloudinary_service import delete_news_image
from ..database import get_db
from .. import crud, models
from .. import schemas
from ..security import require_writer


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
    "/paginated",
    response_model=schemas.NewsPageResponse,
)
def get_news_paginated(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return crud.get_news_page(
        db,
        page=page,
        per_page=per_page,
        category_name=category,
    )


@router.get(
    "/mine",
    response_model=schemas.NewsPageResponse,
)
def get_my_news(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    writer: models.User = Depends(require_writer),
):
    return crud.get_news_page(
        db,
        page=page,
        per_page=per_page,
        author_id=writer.id,
    )


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
    db: Session = Depends(get_db),
    writer: models.User = Depends(require_writer),
):
    return crud.create_news(db, news, author_id=writer.id)


@router.put(
    "/{news_id}",
    response_model=schemas.NewsResponse
)
def update_news(
    news_id: int,
    news: schemas.NewsUpdate,
    db: Session = Depends(get_db),
    writer: models.User = Depends(require_writer),
):
    current_news = crud.get_news_by_id(db, news_id)
    if not current_news:
        raise HTTPException(status_code=404, detail="News tidak ditemukan")
    if current_news.author_id != writer.id:
        raise HTTPException(status_code=403, detail="Anda hanya dapat mengubah berita milik sendiri")

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
async def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    writer: models.User = Depends(require_writer),
):
    news_item = crud.get_news_by_id(db, news_id)
    if not news_item:
        raise HTTPException(
            status_code=404,
            detail="News tidak ditemukan"
        )
    if news_item.author_id != writer.id:
        raise HTTPException(status_code=403, detail="Anda hanya dapat menghapus berita milik sendiri")

    try:
        await delete_news_image(news_item.image_url)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Gambar gagal dihapus dari Cloudinary. Berita tetap tersimpan.",
        ) from exc

    crud.delete_news(db, news_id)

    return {
        "message": "News berhasil dihapus",
        "id": news_id
    }

