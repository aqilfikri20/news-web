import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "../styles/Navbar.css";

function Navbar() {
  const navigate = useNavigate();

  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();

    navigate("/login");
  };

  return (
    <nav className="navbar">

      <div className="container navbar-content">

        {/* Logo */}
        <Link
          to="/"
          className="logo"
        >
          News<span>Hub</span>
        </Link>

        {/* Menu */}
        <div className="nav-menu">

          <Link to="/">
            Home
          </Link>

          <Link to="/">
            Technology
          </Link>

          <Link to="/">
            Business
          </Link>

          <Link to="/">
            Development
          </Link>

        </div>

        {/* Auth */}
        <div className="nav-auth">

          {user ? (
            <>
              <span className="user-name">
                Hi, {user.name}
              </span>

              <button
                onClick={handleLogout}
                className="logout-button"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="login-button"
              >
                Login
              </Link>

              <Link
                to="/register"
                className="register-button"
              >
                Register
              </Link>
            </>
          )}

        </div>

      </div>

    </nav>
  );
}

export default Navbar;
