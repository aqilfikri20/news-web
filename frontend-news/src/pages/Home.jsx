import { useEffect, useState } from "react";
import NewsCard from "../components/NewsCard";
import "../styles/home.css";

function Home() {
  const [newsData, setNewsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_URL}/api/news/`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Gagal mengambil data berita");
        }

        return response.json();
      })
      .then((data) => {
        setNewsData(data);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <main>
      {/* Hero */}
      <section className="hero">
        <div className="container">
          <span className="hero-label">
            BERITA & KEJADIAN TERBARU
          </span>

          <h1>
            Berita Terbaru dan Terkini dari Seluruh Dunia
          </h1>
        </div>
      </section>

      {/* News */}
      <section className="news-section">
        <div className="container">

          <div className="section-header">
            <div>
              <h2>Berita Terbaru</h2>
            </div>

            <button className="view-all">
              View All →
            </button>
          </div>

          {/* Loading */}
          {loading && <p>Loading berita...</p>}

          {/* Error */}
          {error && <p>{error}</p>}

          {/* News */}
          {!loading && !error && (
            <div className="news-grid">
              {newsData.map((news) => (
                <NewsCard
                  key={news.id}
                  news={news}
                />
              ))}
            </div>
          )}

        </div>
      </section>
    </main>
  );
}

export default Home;
