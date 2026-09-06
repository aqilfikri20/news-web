import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import "../styles/news-detail.css";

function NewsDetail() {
  const { id } = useParams();

  const [news, setNews] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        setError(false);

        const response = await fetch(
          `${API_URL}/api/news/${id}`
        );

        if (!response.ok) {
          throw new Error("Berita tidak ditemukan");
        }

        const data = await response.json();

        setNews(data);
      } catch (error) {
        console.error("Gagal mengambil berita:", error);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [id, API_URL]);

  // Loading
  if (loading) {
    return (
      <main className="news-not-found">
        <div className="container">
          <h1>Loading...</h1>
          <p>Sedang mengambil berita.</p>
        </div>
      </main>
    );
  }

  // Berita tidak ditemukan
  if (error || !news) {
    return (
      <main className="news-not-found">
        <div className="container">
          <h1>Berita Tidak Ditemukan</h1>

          <p>
            Berita yang kamu cari tidak tersedia.
          </p>

          <Link to="/" className="back-button">
            ← Kembali ke Home
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="news-detail">

      <div className="container">

        {/* Back */}
        <Link to="/" className="back-link">
          ← Back to Home
        </Link>

        {/* Header */}
        <div className="news-detail-header">

          <div className="news-detail-meta">

            <span className="category">
              {news.category?.name || "Tanpa Kategori"}
            </span>

            <span className="date">
              {new Date(news.created_at).toLocaleDateString(
                "id-ID",
                {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                }
              )}
            </span>

          </div>

          <h1>
            {news.title}
          </h1>

          <p className="news-detail-description">
            {news.description}
          </p>

          <div className="news-author">
            <span>By</span>

            <strong>
              {news.author?.name || "Unknown"}
            </strong>
          </div>

        </div>

        {/* Image */}
        <div className="news-detail-image-wrapper">
          <img
            src={news.image_url}
            alt={news.title}
            className="news-detail-image"
          />
        </div>

        {/* Content */}
        <article className="news-content">

          <p>
            {news.content}
          </p>

        </article>

      </div>

    </main>
  );
}

export default NewsDetail;

