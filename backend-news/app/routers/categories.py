from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud
from .. import schemas
from ..security import require_admin


router = APIRouter(
    prefix="/api/categories",
    tags=["Categories"]
)


# =========================================================
# GET ALL CATEGORIES
# =========================================================

@router.get(
    "/",
    response_model=list[schemas.CategoryResponse]
)
def get_categories(
    db: Session = Depends(get_db)
):
    return crud.get_categories(db)


# =========================================================
# GET CATEGORY BY ID
# =========================================================

@router.get(
    "/{category_id}",
    response_model=schemas.CategoryResponse
)
def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = crud.get_category_by_id(
        db,
        category_id
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category tidak ditemukan"
        )

    return category


# =========================================================
# CREATE CATEGORY
# =========================================================

@router.post(
    "/",
    response_model=schemas.CategoryResponse,
    status_code=201
)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return crud.create_category(
        db,
        category
    )


# =========================================================
# UPDATE CATEGORY
# =========================================================

@router.put(
    "/{category_id}",
    response_model=schemas.CategoryResponse
)
def update_category(
    category_id: int,
    category: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    updated_category = crud.update_category(
        db,
        category_id,
        category
    )

    if not updated_category:
        raise HTTPException(
            status_code=404,
            detail="Category tidak ditemukan"
        )

    return updated_category


# =========================================================
# DELETE CATEGORY
# =========================================================

@router.delete(
    "/{category_id}"
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    deleted_category = crud.delete_category(
        db,
        category_id
    )

    if not deleted_category:
        raise HTTPException(
            status_code=404,
            detail="Category tidak ditemukan"
        )

    return {
        "message": "Category berhasil dihapus",
        "id": category_id
    }

