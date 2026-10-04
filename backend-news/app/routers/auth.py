from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import (
    clear_session_cookie,
    consume_captcha,
    create_captcha,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["Auth"])


def public_user(user: models.User):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "address": user.address,
        "role": user.role,
    }


@router.get("/captcha")
def captcha(db: Session = Depends(get_db)):
    return create_captcha(db)


@router.post("/login")
def login(
    credentials: schemas.LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    if not consume_captcha(db, credentials.captcha_id, credentials.captcha_answer):
        raise HTTPException(status_code=400, detail="CAPTCHA salah atau sudah kedaluwarsa")
    user = db.query(models.User).filter(
        func.lower(models.User.email) == credentials.email.strip().lower()
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email atau password salah")

    valid, needs_upgrade = verify_password(credentials.password, user.password)
    if not valid or user.role not in {"admin", "writer"}:
        raise HTTPException(status_code=401, detail="Email atau password salah")

    if needs_upgrade:
        user.password = hash_password(credentials.password)
        db.commit()
        db.refresh(user)

    token = set_session_cookie(response, user)
    return {
        "message": "Login berhasil",
        "access_token": token,
        "token_type": "bearer",
        "user": public_user(user),
    }


@router.post("/register", status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Konfirmasi password tidak cocok")
    if not consume_captcha(db, user.captcha_id, user.captcha_answer):
        raise HTTPException(status_code=400, detail="CAPTCHA salah atau sudah kedaluwarsa")
    normalized_email = user.email.strip().lower()
    name, phone, address = user.name.strip(), user.phone.strip(), user.address.strip()
    if not name or not phone or not address:
        raise HTTPException(status_code=422, detail="Nama, nomor HP, dan alamat wajib diisi")
    existing_user = db.query(models.User).filter(func.lower(models.User.email) == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    new_user = models.User(
        name=name,
        email=normalized_email,
        phone=phone,
        address=address,
        password=hash_password(user.password),
        role="writer",
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email sudah terdaftar") from exc

    return {"message": "Pendaftaran penulis berhasil", "user": public_user(new_user)}


@router.put("/me")
def update_my_profile(
    profile: schemas.WriterProfileUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role != "writer":
        raise HTTPException(status_code=403, detail="Hanya penulis yang dapat mengubah profil melalui endpoint ini")
    valid, needs_upgrade = verify_password(profile.current_password, user.password)
    if not valid:
        raise HTTPException(status_code=400, detail="Password saat ini salah")

    name, email = profile.name.strip(), profile.email.strip().lower()
    phone, address = profile.phone.strip(), profile.address.strip()
    if not name or not phone or not address:
        raise HTTPException(status_code=422, detail="Nama, nomor HP, dan alamat wajib diisi")
    if db.query(models.User.id).filter(
        func.lower(models.User.email) == email,
        models.User.id != user.id,
    ).first():
        raise HTTPException(status_code=400, detail="Email tersebut sudah digunakan")

    new_password = (profile.new_password or "").strip()
    confirm_password = profile.confirm_password or ""
    if not new_password and confirm_password:
        raise HTTPException(status_code=400, detail="Isi password baru sebelum konfirmasinya")
    if new_password:
        if len(new_password) < 8 or len(new_password) > 128:
            raise HTTPException(status_code=422, detail="Password baru harus terdiri dari 8-128 karakter")
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="Konfirmasi password baru tidak cocok")
        user.password = hash_password(new_password)
    elif needs_upgrade:
        user.password = hash_password(profile.current_password)

    user.name, user.email, user.phone, user.address = name, email, phone, address
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email tersebut sudah digunakan") from exc
    return {"message": "Profil berhasil diperbarui", "user": public_user(user)}


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"message": "Logout berhasil"}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return public_user(user)
