import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool


BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

CLOUDINARY_CONFIGURED = all(
    os.getenv(key)
    for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
)
if CLOUDINARY_CONFIGURED:
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )

MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
CLOUDINARY_FOLDER = "newshub/news"


async def upload_news_image(image: UploadFile | None) -> str | None:
    if not image or not image.filename:
        return None
    if not CLOUDINARY_CONFIGURED:
        raise ValueError(
            "Cloudinary belum dikonfigurasi. Isi CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, dan CLOUDINARY_API_SECRET di backend-news/.env."
        )
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Format gambar yang didukung: JPG, PNG, WEBP, dan GIF.")

    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise ValueError("Ukuran gambar maksimal 5 MB.")
    if not image_bytes:
        raise ValueError("File gambar kosong.")
    image.file.seek(0)

    result = await run_in_threadpool(
        cloudinary.uploader.upload,
        image.file,
        folder=CLOUDINARY_FOLDER,
        public_id=uuid4().hex,
        resource_type="image",
        transformation=[{"quality": "auto", "fetch_format": "auto"}],
    )
    return result["secure_url"]


def _public_id_from_url(image_url: str) -> str | None:
    """Return the public ID for an image in the configured Cloudinary account."""
    parsed = urlparse(image_url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "res.cloudinary.com":
        return None

    parts = [unquote(part) for part in parsed.path.split("/") if part]
    configured_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    if len(parts) < 4 or parts[1] != "image":
        return None
    if configured_cloud_name and parts[0] != configured_cloud_name:
        return None
    try:
        upload_index = parts.index("upload")
    except ValueError:
        return None

    # Cloudinary delivery URLs may have transformations between /upload/ and /v123/.
    version_index = next(
        (index for index in range(upload_index + 1, len(parts)) if re.fullmatch(r"v\d+", parts[index])),
        None,
    )
    if version_index is None:
        raise RuntimeError("URL Cloudinary ini tidak memiliki versi yang diperlukan untuk menghapus gambar dengan aman.")

    asset_parts = parts[version_index + 1:]
    if not asset_parts:
        return None

    final_part = asset_parts[-1]
    stem, separator, extension = final_part.rpartition(".")
    if separator and extension.lower() in {"jpg", "jpeg", "png", "webp", "gif", "avif"}:
        asset_parts[-1] = stem
    return "/".join(asset_parts)


async def delete_news_image(image_url: str | None) -> bool:
    """Delete a managed Cloudinary image; return False for external/legacy URLs."""
    if not image_url:
        return False
    public_id = _public_id_from_url(image_url)
    if not public_id:
        return False
    if not CLOUDINARY_CONFIGURED:
        raise RuntimeError("Cloudinary belum dikonfigurasi; gambar tidak dihapus.")

    result = await run_in_threadpool(
        cloudinary.uploader.destroy,
        public_id,
        resource_type="image",
        invalidate=True,
    )
    if result.get("result") not in {"ok", "not found"}:
        raise RuntimeError(f"Cloudinary tidak menghapus gambar (status: {result.get('result', 'unknown')}).")
    return result.get("result") == "ok"
