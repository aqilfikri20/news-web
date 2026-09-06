import { useEffect, useState } from "react";
import "../styles/create-news.css";

function CreateNews() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [categoryId, setCategoryId] = useState("");

  const [categories, setCategories] = useState([]);

  const [loading, setLoading] = useState(false);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const API_URL = import.meta.env.VITE_API_URL;

  // =========================
  // AMBIL DATA CATEGORY
  // =========================

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/categories/`
        );

        if (!response.ok) {
          throw new Error("Gagal mengambil kategori");
        }

        const data = await response.json();

        setCategories(data);
      } catch (error) {
        console.error(error);
        setError("Gagal mengambil data kategori.");
      } finally {
        setLoadingCategories(false);
      }
    };

    fetchCategories();
  }, [API_URL]);

  // =========================
  // SUBMIT NEWS
  // =========================

  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");
    setSuccess("");

    const newNews = {
      title: title,
      description: description,
      content: content,
      image_url: imageUrl,
      category_id: Number(categoryId),

      // sementara menggunakan Admin
      author_id: 1,
    };

    try {
      const response = await fetch(
        `${API_URL}/api/news/`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify(newNews),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Gagal membuat berita"
        );
      }

      console.log("News berhasil dibuat:", data);

      setSuccess("Berita berhasil dibuat!");

      // Reset form
      setTitle("");
      setDescription("");
      setContent("");
      setImageUrl("");
      setCategoryId("");

    } catch (error) {
      console.error("Gagal membuat berita:", error);

      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="create-news-page">
      <div className="container">

        <div className="create-news-header">
          <span className="section-label">
            ADMIN
          </span>

          <h1>Create News</h1>

          <p>
            Buat berita baru untuk dipublikasikan.
          </p>
        </div>

        {/* Success */}
        {success && (
          <div className="success-message">
            {success}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form
          className="news-form"
          onSubmit={handleSubmit}
        >

          {/* Title */}
          <div className="form-group">
            <label htmlFor="title">
              Title
            </label>

            <input
              id="title"
              type="text"
              placeholder="Masukkan judul berita"
              value={title}
              onChange={(e) =>
                setTitle(e.target.value)
              }
              required
            />
          </div>

          {/* Description */}
          <div className="form-group">
            <label htmlFor="description">
              Description
            </label>

            <textarea
              id="description"
              placeholder="Masukkan deskripsi singkat"
              value={description}
              onChange={(e) =>
                setDescription(e.target.value)
              }
              rows="4"
              required
            />
          </div>

          {/* Content */}
          <div className="form-group">
            <label htmlFor="content">
              Content
            </label>

            <textarea
              id="content"
              placeholder="Masukkan isi berita"
              value={content}
              onChange={(e) =>
                setContent(e.target.value)
              }
              rows="10"
              required
            />
          </div>

          {/* Image */}
          <div className="form-group">
            <label htmlFor="imageUrl">
              Image URL
            </label>

            <input
              id="imageUrl"
              type="url"
              placeholder="https://example.com/image.jpg"
              value={imageUrl}
              onChange={(e) =>
                setImageUrl(e.target.value)
              }
              required
            />
          </div>

          {/* Category */}
          <div className="form-group">
            <label htmlFor="category">
              Category
            </label>

            <select
              id="category"
              value={categoryId}
              onChange={(e) =>
                setCategoryId(e.target.value)
              }
              required
              disabled={loadingCategories}
            >
              <option value="">
                {loadingCategories
                  ? "Loading kategori..."
                  : "Pilih kategori"}
              </option>

              {categories.map((category) => (
                <option
                  key={category.id}
                  value={category.id}
                >
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          {/* Button */}
          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "Publishing..."
              : "Publish News"}
          </button>

        </form>

      </div>
    </main>
  );
}

export default CreateNews;
