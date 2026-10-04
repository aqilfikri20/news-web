import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import NewsCard from "../components/NewsCard";
import Pagination from "../components/Pagination";
import "../styles/home.css";

const PAGE_SIZE = 10;

function Home() {
  const { categoryName } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const [newsPage, setNewsPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(PAGE_SIZE),
    });
    if (categoryName) params.set("category", categoryName);

    setLoading(true);
    setError(null);

    fetch(`${API_URL}/api/news/paginated?${params}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Gagal mengambil data berita");
        return response.json();
      })
      .then((data) => {
        setNewsPage(data);
        if (data.page !== page) {
          setSearchParams((current) => {
            const next = new URLSearchParams(current);
            if (data.page === 1) next.delete("page");
            else next.set("page", String(data.page));
            return next;
          }, { replace: true });
        }
      })
      .catch((fetchError) => {
        if (fetchError.name !== "AbortError") setError(fetchError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [API_URL, categoryName, page, setSearchParams]);

  const changePage = (nextPage) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (nextPage === 1) next.delete("page");
      else next.set("page", String(nextPage));
      return next;
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main>
      <section className="hero">
        <div className="container">
          <span className="hero-label">BERITA &amp; KEJADIAN TERBARU</span>
          <h1>Berita Terbaru dan Terkini dari Seluruh Dunia</h1>
        </div>
      </section>

      <section className="news-section">
        <div className="container">
          <div className="section-header">
            <div>
              <h2>{categoryName ? `Berita ${categoryName}` : "Berita Terbaru"}</h2>
              {newsPage && <p className="news-count">Menampilkan {newsPage.total === 0 ? 0 : (newsPage.page - 1) * PAGE_SIZE + 1}–{Math.min(newsPage.page * PAGE_SIZE, newsPage.total)} dari {newsPage.total} berita</p>}
            </div>
          </div>

          {loading && <p>Loading berita...</p>}
          {error && <p className="news-error">{error}</p>}

          {!loading && !error && newsPage && (
            <>
              {newsPage.items.length > 0 ? (
                <div className="news-grid">
                  {newsPage.items.map((news) => (
                    <NewsCard key={news.id} news={news} />
                  ))}
                </div>
              ) : (
                <p>Belum ada berita{categoryName ? " untuk kategori ini" : ""}.</p>
              )}

              <Pagination
                page={newsPage.page}
                totalPages={newsPage.total_pages}
                onPageChange={changePage}
              />
            </>
          )}
        </div>
      </section>
    </main>
  );
}

export default Home;
