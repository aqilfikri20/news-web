from pathlib import Path
import os

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from . import models
from .cloudinary_service import delete_news_image, upload_news_image
from .database import get_db
from .routers import auth, categories, news
from .security import (
    SESSION_COOKIE,
    decode_session_token,
    consume_captcha,
    create_captcha,
    hash_password,
    set_session_cookie,
    verify_password,
)


BACKEND_DIR = Path(__file__).resolve().parent.parent
NEWS_PAGE_SIZE = 10
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080").rstrip("/")
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8080,http://127.0.0.1:8080"
)

app = FastAPI(
    title="NewsHub API",
    description="RESTful API untuk NewsHub",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(news.router)
app.include_router(categories.router)
app.mount("/static", StaticFiles(directory=str(BACKEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BACKEND_DIR / "templates"))
templates.env.globals["frontend_url"] = FRONTEND_URL


def cookie_user(request: Request, db: Session):
    payload = decode_session_token(request.cookies.get(SESSION_COOKIE))
    if not payload:
        return None
    user = db.query(models.User).filter(models.User.id == payload.get("sub")).first()
    if not user or user.role != payload.get("role"):
        return None
    return user


def render_admin(request, db, *, error=None, success=None):
    current_user = cookie_user(request, db)
    is_admin = bool(current_user and current_user.role == "admin")
    captcha = create_captcha(db) if not is_admin else None
    writers = (
        db.query(models.User)
        .filter(models.User.role == "writer")
        .order_by(models.User.created_at.desc(), models.User.id.desc())
        .all()
        if is_admin else []
    )
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "logged_in": is_admin,
            "admin": current_user if is_admin else None,
            "writers": writers,
            "captcha": captcha,
            "error": error,
            "success": success or request.query_params.get("success"),
        },
    )


def render_writer_auth(request, db, *, mode, error=None):
    captcha = create_captcha(db)
    return templates.TemplateResponse(
        request=request,
        name="writer_auth.html",
        context={"mode": mode, "error": error, "captcha": captcha},
    )


def render_writer_dashboard(request, db, writer, *, mode="list", error=None, editing=None, page=1):
    page = max(1, page)
    total = 0
    total_pages = 1
    pagination_pages = []
    news_items = []
    categories = []

    if mode == "list":
        total = (
            db.query(func.count(models.News.id))
            .filter(models.News.author_id == writer.id)
            .scalar()
            or 0
        )
        total_pages = max(1, (total + NEWS_PAGE_SIZE - 1) // NEWS_PAGE_SIZE)
        page = min(page, total_pages)
        news_items = (
            db.query(models.News)
            .options(joinedload(models.News.category))
            .filter(models.News.author_id == writer.id)
            .order_by(models.News.created_at.desc(), models.News.id.desc())
            .offset((page - 1) * NEWS_PAGE_SIZE)
            .limit(NEWS_PAGE_SIZE)
            .all()
        )
        pagination_pages = range(max(1, page - 2), min(total_pages, page + 2) + 1)
    else:
        categories = db.query(models.Category).order_by(models.Category.name).all()

    return templates.TemplateResponse(
        request=request,
        name="writer_dashboard.html",
        context={
            "writer": writer,
            "mode": mode,
            "editing": editing,
            "error": error,
            "success": request.query_params.get("success"),
            "news_items": news_items,
            "categories": categories,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "pagination_pages": pagination_pages,
        },
    )


def redirect(location: str):
    return RedirectResponse(url=location, status_code=303)


@app.get("/")
def root():
    return redirect("/dashboard")


# Admin dashboard: admins are provisioned directly in the database and can only log in.
@app.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = cookie_user(request, db)
    if user and user.role == "writer":
        return redirect("/writer/dashboard")
    return render_admin(request, db)


@app.post("/dashboard/login")
def admin_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    captcha_id: str = Form(...),
    captcha_answer: str = Form(...),
    db: Session = Depends(get_db),
):
    if not consume_captcha(db, captcha_id, captcha_answer):
        return render_admin(request, db, error="CAPTCHA salah atau sudah kedaluwarsa. Silakan coba lagi.")
    user = db.query(models.User).filter(
        func.lower(models.User.email) == email.strip().lower(),
        models.User.role == "admin",
    ).first()
    if not user:
        return render_admin(request, db, error="Email admin atau password salah.")
    valid, needs_upgrade = verify_password(password, user.password)
    if not valid:
        return render_admin(request, db, error="Email admin atau password salah.")
    if needs_upgrade:
        user.password = hash_password(password)
        db.commit()

    response = redirect("/dashboard")
    set_session_cookie(response, user)
    return response


@app.post("/dashboard/logout")
def admin_logout():
    response = redirect("/dashboard")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.post("/dashboard/writers/create")
def admin_create_writer(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = cookie_user(request, db)
    if not admin or admin.role != "admin":
        return redirect("/dashboard")
    name, email, phone, address = name.strip(), email.strip().lower(), phone.strip(), address.strip()
    if not name or len(name) > 100 or not phone or len(phone) > 30 or not address:
        return render_admin(request, db, error="Nama, nomor HP, dan alamat wajib diisi. Panjang nama maksimal 100 dan nomor HP 30 karakter.")
    if len(password) < 8 or len(password) > 128:
        return render_admin(request, db, error="Password penulis harus terdiri dari 8-128 karakter.")
    if password != confirm_password:
        return render_admin(request, db, error="Konfirmasi password penulis tidak cocok.")
    if db.query(models.User.id).filter(func.lower(models.User.email) == email).first():
        return render_admin(request, db, error="Email tersebut sudah digunakan.")

    db.add(models.User(
        name=name,
        email=email,
        phone=phone,
        address=address,
        password=hash_password(password),
        role="writer",
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_admin(request, db, error="Akun penulis gagal dibuat. Pastikan email belum terdaftar.")
    return redirect("/dashboard?success=Akun+penulis+berhasil+ditambahkan")


@app.post("/dashboard/writers/{writer_id}/delete")
def admin_delete_writer(
    writer_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = cookie_user(request, db)
    if not admin or admin.role != "admin":
        return redirect("/dashboard")
    writer = db.query(models.User).filter(
        models.User.id == writer_id,
        models.User.role == "writer",
    ).first()
    if not writer:
        return render_admin(request, db, error="Penulis tidak ditemukan.")

    # Keep published stories and their images while removing the writer account.
    db.query(models.News).filter(models.News.author_id == writer.id).update(
        {models.News.author_id: admin.id},
        synchronize_session=False,
    )
    db.delete(writer)
    db.commit()
    return redirect("/dashboard?success=Akun+penulis+dihapus.+Beritanya+dialihkan+ke+admin")


# Writer sign-up, sign-in, and own-news dashboard.
@app.get("/writer")
def writer_home(request: Request, db: Session = Depends(get_db)):
    user = cookie_user(request, db)
    return redirect("/writer/dashboard" if user and user.role == "writer" else "/writer/login")


@app.get("/writer/signup")
def writer_signup_page(request: Request, db: Session = Depends(get_db)):
    user = cookie_user(request, db)
    if user and user.role == "writer":
        return redirect("/writer/dashboard")
    return render_writer_auth(request, db, mode="signup")


@app.post("/writer/signup")
def writer_signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    captcha_id: str = Form(...),
    captcha_answer: str = Form(...),
    db: Session = Depends(get_db),
):
    name, email, phone, address = name.strip(), email.strip().lower(), phone.strip(), address.strip()
    if not name or len(name) > 100 or not phone or len(phone) > 30 or not address:
        return render_writer_auth(request, db, mode="signup", error="Semua data profil wajib diisi. Panjang nama maksimal 100 dan nomor HP 30 karakter.")
    if len(password) < 8 or len(password) > 128:
        return render_writer_auth(request, db, mode="signup", error="Password harus terdiri dari 8-128 karakter.")
    if password != confirm_password:
        return render_writer_auth(request, db, mode="signup", error="Konfirmasi password tidak cocok.")
    if not consume_captcha(db, captcha_id, captcha_answer):
        return render_writer_auth(request, db, mode="signup", error="CAPTCHA salah atau sudah kedaluwarsa. Silakan coba lagi.")
    if db.query(models.User.id).filter(func.lower(models.User.email) == email).first():
        return render_writer_auth(request, db, mode="signup", error="Email tersebut sudah terdaftar.")

    writer = models.User(
        name=name,
        email=email,
        phone=phone,
        address=address,
        password=hash_password(password),
        role="writer",
    )
    db.add(writer)
    try:
        db.commit()
        db.refresh(writer)
    except IntegrityError:
        db.rollback()
        return render_writer_auth(request, db, mode="signup", error="Pendaftaran gagal. Email mungkin sudah digunakan.")
    response = redirect("/writer/dashboard")
    set_session_cookie(response, writer)
    return response


@app.get("/writer/login")
def writer_login_page(request: Request, db: Session = Depends(get_db)):
    user = cookie_user(request, db)
    if user and user.role == "writer":
        return redirect("/writer/dashboard")
    return render_writer_auth(request, db, mode="login")


@app.post("/writer/login")
def writer_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    captcha_id: str = Form(...),
    captcha_answer: str = Form(...),
    db: Session = Depends(get_db),
):
    if not consume_captcha(db, captcha_id, captcha_answer):
        return render_writer_auth(request, db, mode="login", error="CAPTCHA salah atau sudah kedaluwarsa. Silakan coba lagi.")
    writer = db.query(models.User).filter(
        func.lower(models.User.email) == email.strip().lower(),
        models.User.role == "writer",
    ).first()
    valid = False
    needs_upgrade = False
    if writer:
        valid, needs_upgrade = verify_password(password, writer.password)
    if not writer or not valid:
        return render_writer_auth(request, db, mode="login", error="Email atau password salah.")
    if needs_upgrade:
        writer.password = hash_password(password)
        db.commit()
    response = redirect("/writer/dashboard")
    set_session_cookie(response, writer)
    return response


@app.post("/writer/logout")
def writer_logout():
    response = redirect("/writer/login")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/writer/dashboard")
def writer_dashboard(
    request: Request,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    # Use validated query page for the same server-side 10-row pagination.
    return render_writer_dashboard(request, db, writer, mode="list", page=page)


@app.get("/writer/profile")
def writer_profile_page(request: Request, db: Session = Depends(get_db)):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    return templates.TemplateResponse(
        request=request,
        name="writer_profile.html",
        context={"writer": writer, "error": None, "success": request.query_params.get("success")},
    )


@app.post("/writer/profile")
def writer_profile_update(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    name, email = name.strip(), email.strip().lower()
    phone, address = phone.strip(), address.strip()
    valid, needs_upgrade = verify_password(current_password, writer.password)
    error = None
    if not valid:
        error = "Password saat ini salah."
    elif not name or len(name) > 100 or not email or not phone or len(phone) > 30 or not address:
        error = "Nama, email, nomor HP, dan alamat wajib diisi. Nama maksimal 100 dan nomor HP 30 karakter."
    elif db.query(models.User.id).filter(
        func.lower(models.User.email) == email,
        models.User.id != writer.id,
    ).first():
        error = "Email tersebut sudah digunakan."
    elif new_password and (len(new_password) < 8 or len(new_password) > 128):
        error = "Password baru harus terdiri dari 8-128 karakter."
    elif new_password != confirm_password:
        error = "Konfirmasi password baru tidak cocok."

    if error:
        return templates.TemplateResponse(
            request=request,
            name="writer_profile.html",
            context={"writer": writer, "error": error, "success": None},
        )

    writer.name, writer.email, writer.phone, writer.address = name, email, phone, address
    if new_password:
        writer.password = hash_password(new_password)
    elif needs_upgrade:
        writer.password = hash_password(current_password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="writer_profile.html",
            context={"writer": writer, "error": "Email tersebut sudah digunakan.", "success": None},
        )
    return redirect("/writer/profile?success=Profil+berhasil+diperbarui")


@app.get("/writer/news/new")
def writer_new_news(request: Request, db: Session = Depends(get_db)):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    return render_writer_dashboard(request, db, writer, mode="create")


@app.get("/writer/news/{news_id}/edit")
def writer_edit_news(news_id: int, request: Request, db: Session = Depends(get_db)):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    item = db.query(models.News).filter(
        models.News.id == news_id,
        models.News.author_id == writer.id,
    ).first()
    if not item:
        return render_writer_dashboard(request, db, writer, error="Berita tidak ditemukan atau bukan milik Anda.")
    return render_writer_dashboard(request, db, writer, mode="edit", editing=item)


async def save_writer_news(request, db, writer, *, news_id, title, description, content, image, category_id):
    title, content = title.strip(), content.strip()
    description = description.strip() or None
    item = None
    if news_id:
        item = db.query(models.News).filter(
            models.News.id == news_id,
            models.News.author_id == writer.id,
        ).first()
        if not item:
            return render_writer_dashboard(request, db, writer, error="Berita tidak ditemukan atau bukan milik Anda.")
    if not title or len(title) > 255 or not content:
        return render_writer_dashboard(request, db, writer, mode="edit" if news_id else "create", editing=item, error="Judul (maksimal 255 karakter) dan isi berita wajib diisi.")
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        return render_writer_dashboard(request, db, writer, mode="edit" if news_id else "create", editing=item, error="Pilih kategori yang tersedia.")

    try:
        new_image_url = await upload_news_image(image)
    except ValueError as exc:
        return render_writer_dashboard(request, db, writer, mode="edit" if news_id else "create", editing=item, error=str(exc))
    except Exception:
        return render_writer_dashboard(request, db, writer, mode="edit" if news_id else "create", editing=item, error="Upload gambar gagal. Periksa konfigurasi Cloudinary dan koneksi.")
    if not item and not new_image_url:
        return render_writer_dashboard(request, db, writer, mode="create", error="Gambar berita wajib dipilih.")

    previous_image_url = item.image_url if item else None
    if item is None:
        item = models.News(author_id=writer.id)
    item.title = title
    item.description = description
    item.content = content
    item.category_id = category_id
    if new_image_url:
        item.image_url = new_image_url
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if new_image_url:
            try:
                await delete_news_image(new_image_url)
            except Exception:
                pass
        return render_writer_dashboard(request, db, writer, mode="edit" if news_id else "create", editing=item if news_id else None, error="Berita tidak dapat disimpan karena data tidak valid.")

    if new_image_url and previous_image_url:
        try:
            await delete_news_image(previous_image_url)
        except Exception:
            item.image_url = previous_image_url
            db.commit()
            try:
                await delete_news_image(new_image_url)
            except Exception:
                pass
            return render_writer_dashboard(request, db, writer, mode="edit", editing=item, error="Gambar lama gagal dihapus dari Cloudinary; gambar lama tetap digunakan.")
    return redirect("/writer/dashboard?success=Berita+berhasil+disimpan")


@app.post("/writer/news/create")
async def writer_create_news(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    content: str = Form(...),
    image: UploadFile | None = File(None),
    category_id: int = Form(...),
    db: Session = Depends(get_db),
):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    return await save_writer_news(request, db, writer, news_id=None, title=title, description=description,
                                  content=content, image=image, category_id=category_id)


@app.post("/writer/news/{news_id}/update")
async def writer_update_news(
    news_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    content: str = Form(...),
    image: UploadFile | None = File(None),
    category_id: int = Form(...),
    db: Session = Depends(get_db),
):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    return await save_writer_news(request, db, writer, news_id=news_id, title=title, description=description,
                                  content=content, image=image, category_id=category_id)


@app.post("/writer/news/{news_id}/delete")
async def writer_delete_news(news_id: int, request: Request, db: Session = Depends(get_db)):
    writer = cookie_user(request, db)
    if not writer or writer.role != "writer":
        return redirect("/writer/login")
    item = db.query(models.News).filter(
        models.News.id == news_id,
        models.News.author_id == writer.id,
    ).first()
    if not item:
        return render_writer_dashboard(request, db, writer, error="Berita tidak ditemukan atau bukan milik Anda.")
    try:
        await delete_news_image(item.image_url)
    except Exception:
        return render_writer_dashboard(request, db, writer, error="Gambar gagal dihapus dari Cloudinary. Berita tetap tersimpan.")
    db.delete(item)
    db.commit()
    return redirect("/writer/dashboard?success=Berita+dan+gambarnya+berhasil+dihapus")
