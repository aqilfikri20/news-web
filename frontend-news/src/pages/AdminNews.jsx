import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "../styles/admin.css";

function AdminNews() {
  const [news, setNews] = useState([]);

  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");

  const API_URL = import.meta.env.VITE_API_URL;

  // =========================
  // GET NEWS
  // =========================

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          `${API_URL}/api/news/`
        );

        if (!response.ok) {
          throw new Error(
            "Gagal mengambil data berita"
          );
        }

        const data = await response.json();

        setNews(data);

      } catch (error) {
        console.error(
          "Gagal mengambil berita:",
          error
        );

        setError(error.message);

      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [API_URL]);

  // =========================
  // DELETE NEWS
  // =========================

  const handleDelete = async (id) => {
    const confirmDelete = window.confirm(
      "Apakah kamu yakin ingin menghapus berita ini?"
    );

    if (!confirmDelete) {
      return;
    }

    try {
      setDeletingId(id);
      setError("");

      const response = await fetch(
        `${API_URL}/api/news/${id}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Gagal menghapus berita"
        );
      }

      // Hapus dari tampilan setelah berhasil
      setNews((currentNews) =>
        currentNews.filter(
          (item) => item.id !== id
        )
      );

    } catch (error) {
      console.error(
        "Gagal menghapus berita:",
        error
      );

      setError(error.message);

    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main className="admin-page">
      <div className="container">

        {/* Header */}
        <div className="admin-header">

          <div>
            <span className="section-label">
              ADMIN PANEL
            </span>

            <h1>News Management</h1>

            <p>
              Kelola berita yang ada di website.
            </p>
          </div>

          <Link
            to="/admin/news/create"
            className="create-news-button"
          >
            + Create News
          </Link>

        </div>

        {/* Error */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="empty-news">
            <h2>Loading...</h2>

            <p>
              Sedang mengambil data berita.
            </p>
          </div>
        )}

        {/* Table */}
        {!loading && news.length > 0 && (
          <div className="admin-table-wrapper">

            <table className="admin-table">

              <thead>
                <tr>
                  <th>ID</th>
                  <th>News</th>
                  <th>Category</th>
                  <th>Author</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>

                {news.map((item) => (
                  <tr key={item.id}>

                    {/* ID */}
                    <td className="news-id">
                      #{item.id}
                    </td>

                    {/* News */}
                    <td>
                      <div className="admin-news-info">

                        <img
                          src={item.image_url}
                          alt={item.title}
                        />

                        <div>
                          <strong>
                            {item.title}
                          </strong>

                          <p>
                            {item.description}
                          </p>
                        </div>

                      </div>
                    </td>

                    {/* Category */}
                    <td>
                      <span className="admin-category">
                        {item.category?.name ||
                          "Tanpa Kategori"}
                      </span>
                    </td>

                    {/* Author */}
                    <td>
                      {item.author?.name ||
                        "Unknown"}
                    </td>

                    {/* Date */}
                    <td>
                      {item.created_at
                        ? new Date(
                            item.created_at
                          ).toLocaleDateString(
                            "id-ID",
                            {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                            }
                          )
                        : "-"}
                    </td>

                    {/* Action */}
                    <td>
                      <div className="admin-actions">

                        {/* View */}
                        <Link
                          to={`/news/${item.id}`}
                          className="action-view"
                        >
                          View
                        </Link>

                        {/* Edit */}
                        <Link
                          to={`/admin/news/edit/${item.id}`}
                          className="action-edit"
                        >
                          Edit
                        </Link>

                        {/* Delete */}
                        <button
                          className="action-delete"
                          onClick={() =>
                            handleDelete(item.id)
                          }
                          disabled={
                            deletingId === item.id
                          }
                        >
                          {deletingId === item.id
                            ? "Deleting..."
                            : "Delete"}
                        </button>

                      </div>
                    </td>

                  </tr>
                ))}

              </tbody>

            </table>

          </div>
        )}

        {/* Empty state */}
        {!loading && news.length === 0 && (
          <div className="empty-news">

            <h2>Tidak ada berita</h2>

            <p>
              Belum ada berita yang tersedia.
            </p>

            <Link
              to="/admin/news/create"
              className="create-news-button"
            >
              + Create News
            </Link>

          </div>
        )}

      </div>
    </main>
  );
}

export default AdminNews;

