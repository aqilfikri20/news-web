import { useState } from "react";
import { NavLink, Link } from "react-router-dom";
import "../styles/navbar.css";

const categories = ["Technology", "Business", "Development"];

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const backendUrl = (
    import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || ""
  ).replace(/\/$/, "");
  const closeMenu = () => setMenuOpen(false);

  return (
    <nav className={`navbar ${menuOpen ? "menu-open" : ""}`}>
      <div className="container navbar-content">
        <Link to="/" className="logo" onClick={closeMenu}>
          News<span>Hub</span>
        </Link>

        <button
          type="button"
          className="nav-toggle"
          aria-label={menuOpen ? "Tutup menu navigasi" : "Buka menu navigasi"}
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>

        <div className="nav-menu" id="primary-navigation">
          <NavLink to="/" end onClick={closeMenu}>Beranda</NavLink>
          {categories.map((category) => (
            <NavLink
              key={category}
              to={`/category/${category}`}
              onClick={closeMenu}
            >
              {category}
            </NavLink>
          ))}
        </div>

        <div className="nav-auth">
          <a className="portal-button" href={`${backendUrl}/dashboard`}>
            Portal pengelola
          </a>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
