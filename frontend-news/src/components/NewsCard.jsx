import { Link } from "react-router-dom";

function NewsCard({ news }) {
  const formattedDate = news.created_at
    ? new Date(news.created_at).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "";

  return (
    <article className="news-card">

      <img
        src={news.image_url || "/news-placeholder.svg"}
        alt={news.title}
        className="news-image"
        onError={(event) => { event.currentTarget.src = "/news-placeholder.svg"; }}
      />

      <div className="news-body">

        <div className="news-meta">
          <span className="category">
            {news.category?.name || "Umum"}
          </span>

          <span className="date">
            {formattedDate}
          </span>
        </div>

        <h2>
          {news.title}
        </h2>

        <p>
          {news.description}
        </p>

        <Link
          to={`/news/${news.id}`}
          className="read-more"
        >
          Read More →
        </Link>

      </div>

    </article>
  );
}

export default NewsCard;
