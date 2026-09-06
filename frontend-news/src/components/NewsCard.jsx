import { Link } from "react-router-dom";

function NewsCard({ news }) {
  return (
    <article className="news-card">

      <img
        src={news.image_url}
        alt={news.title}
        className="news-image"
      />

      <div className="news-body">

        <div className="news-meta">
          <span className="category">
            {news.category.name}
          </span>

          <span className="date">
            {news.created_at}
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