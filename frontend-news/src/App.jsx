import { BrowserRouter, Routes, Route } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import NewsDetail from "./pages/NewsDetail";
import Navbar from "./components/Navbar";
import CreateNews from "./pages/CreateNews";
import AdminNews from "./pages/AdminNews";

function App() {
  return (
    <AuthProvider>

      <BrowserRouter>

        <Navbar />

        <Routes>

          {/* Home */}
          <Route
            path="/"
            element={<Home />}
          />

          {/* Authentication */}
          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/register"
            element={<Register />}
          />

          {/* News */}
          <Route
            path="/news/:id"
            element={<NewsDetail />}
          />

          {/* Admin */}
          <Route
            path="/admin/news"
            element={<AdminNews />}
          />

          <Route
            path="/admin/news/create"
            element={<CreateNews />}
          />

        </Routes>

      </BrowserRouter>

    </AuthProvider>
  );
}

export default App;