from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sympy import python
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from . import models
from . import crud
from . import schemas
from .database import get_db
from .models import User
from .routers import auth
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .routers import news
from .routers import categories


app = FastAPI(
    title="NewsHub API",
    description="RESTful API untuk NewsHub",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(news.router)
app.include_router(categories.router)

# =========================
# STATIC & TEMPLATE
# =========================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)


# =========================
# DASHBOARD
# =========================

@app.get("/dashboard")
def dashboard(request: Request):

    logged_in = request.cookies.get("admin_logged_in") == "true"

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "logged_in": logged_in,
            "error": None
        }
    )




# =========================
# LOGIN ADMIN
# =========================

@app.post("/dashboard/login")
def dashboard_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == email,
        User.role == "admin"
    ).first()

    # Admin tidak ditemukan
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": False,
                "error": "Email admin tidak ditemukan."
            }
        )

    # Password salah
    if user.password != password:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": False,
                "error": "Password salah."
            }
        )

    # Login berhasil
    response = RedirectResponse(
        url="/dashboard",
        status_code=303
    )

    response.set_cookie(
        key="admin_logged_in",
        value="true",
        httponly=True
    )

    return response


# =========================
# LOGOUT
# =========================

@app.post("/dashboard/logout")
def dashboard_logout():

    response = RedirectResponse(
        url="/dashboard",
        status_code=303
    )

    response.delete_cookie(
        key="admin_logged_in"
    )

    return response


@app.post("/dashboard/upload")
async def dashboard_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # =========================================
    # CEK LOGIN ADMIN
    # =========================================

    logged_in = request.cookies.get("admin_logged_in") == "true"

    if not logged_in:
        return RedirectResponse(
            url="/dashboard",
            status_code=303
        )

    # =========================================
    # CEK FILE
    # =========================================

    if not file.filename:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": "Tidak ada file yang dipilih.",
                "success": None
            }
        )

    if not file.filename.lower().endswith(".json"):
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": "File harus berformat JSON.",
                "success": None
            }
        )

    try:
        # =========================================
        # BACA JSON
        # =========================================

        content = await file.read()

        data = json.loads(content)

        if not isinstance(data, list):
            raise ValueError(
                "Format JSON harus berupa array []."
            )

        total_news = 0
        total_categories = 0

        # =========================================
        # LOOP DATA BERITA
        # =========================================

        for item in data:

            # =====================================
            # AMBIL CATEGORY DARI JSON
            # =====================================

            category_data = item["category"]

            category_id = category_data["id"]
            category_name = category_data["name"]

            # =====================================
            # CEK CATEGORY DI DATABASE
            # =====================================

            category = db.query(models.Category).filter(
                models.Category.id == category_id
            ).first()

            # =====================================
            # JIKA BELUM ADA → BUAT CATEGORY
            # =====================================

            if not category:

                category = models.Category(
                    id=category_id,
                    name=category_name
                )

                db.add(category)

                # Agar bisa langsung digunakan
                db.flush()

                total_categories += 1

            # =====================================
            # AMBIL AUTHOR
            # =====================================

            author_data = item["author"]

            author_id = author_data["id"]

            # =====================================
            # CEK AUTHOR
            # =====================================

            author = db.query(models.User).filter(
                models.User.id == author_id
            ).first()

            if not author:
                raise ValueError(
                    f"Author dengan id {author_id} "
                    f"belum ada di database."
                )

            # =====================================
            # BUAT DATA NEWS
            # =====================================

            news_data = schemas.NewsCreate(
                title=item["title"],
                description=item.get("description"),
                content=item["content"],
                image_url=item.get("image_url"),
                category_id=category_id,
                author_id=author_id
            )

            # =====================================
            # INSERT NEWS
            # =====================================

            crud.create_news(
                db,
                news_data
            )

            total_news += 1

        # =========================================
        # BERHASIL
        # =========================================

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": None,
                "success": (
                    f"{total_news} berita berhasil diupload. "
                    f"{total_categories} kategori baru ditambahkan."
                )
            }
        )

    # =========================================
    # JSON INVALID
    # =========================================

    except json.JSONDecodeError:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": "File JSON tidak valid.",
                "success": None
            }
        )

    # =========================================
    # FIELD TIDAK DITEMUKAN
    # =========================================

    except KeyError as e:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": f"Field JSON tidak ditemukan: {e}",
                "success": None
            }
        )

    # =========================================
    # ERROR VALIDASI
    # =========================================

    except ValueError as e:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": str(e),
                "success": None
            }
        )

    # =========================================
    # ERROR DATABASE / LAINNYA
    # =========================================

    except Exception as e:

        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "logged_in": True,
                "error": f"Gagal mengupload berita: {str(e)}",
                "success": None
            }
        )



@app.get("/")
def root():
    return {
        "message": "NewsHub API is running"
    }
