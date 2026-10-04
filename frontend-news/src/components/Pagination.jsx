import "../styles/pagination.css";

function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  const firstPage = Math.max(1, page - 2);
  const lastPage = Math.min(totalPages, page + 2);
  const pages = Array.from(
    { length: lastPage - firstPage + 1 },
    (_, index) => firstPage + index
  );

  return (
    <nav className="pagination" aria-label="Navigasi halaman berita">
      <button
        type="button"
        className="pagination-button"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        Sebelumnya
      </button>

      {pages.map((pageNumber) => (
        <button
          type="button"
          key={pageNumber}
          className={`pagination-button page-number ${pageNumber === page ? "current" : ""}`}
          onClick={() => onPageChange(pageNumber)}
          aria-current={pageNumber === page ? "page" : undefined}
          aria-label={`Halaman ${pageNumber}`}
        >
          {pageNumber}
        </button>
      ))}

      <button
        type="button"
        className="pagination-button"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        Selanjutnya
      </button>
      <span className="pagination-status">Halaman {page} dari {totalPages}</span>
    </nav>
  );
}

export default Pagination;
