# Cloudinary setup

1. Install backend dependencies: `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`.
3. In the Cloudinary Console, copy the product environment's cloud name, API key, and API secret into the matching variables in `.env`.
4. Restart the FastAPI server.
5. Sign in as a writer at `/writer/dashboard` and create or edit a news item with an image file (JPG, PNG, WEBP, or GIF; maximum 5 MB).

The dashboard uploads the image to Cloudinary and saves its HTTPS delivery URL in the existing `news.image_url` database column. The news API returns that URL, which the frontend uses for cards, admin thumbnails, and article pages. No database migration is needed.

Deleting a news item from the writer dashboard or API deletes its Cloudinary image before removing the database row. Replacing an image also deletes its previous Cloudinary asset. If Cloudinary deletion fails, the news item is kept and the dashboard/API reports the failure.

Keep `.env` private and do not commit Cloudinary credentials.
