import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

function PrivateRoute({ children }) {
  const { token, loading } = useAuth();

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div>
          <div className="header">
            <h1>Moderator Dashboard</h1>
            <div className="user-info">
              <LogoutButton />
            </div>
          </div>
          <AppRoutes />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

function LogoutButton() {
  const { logout, user } = useAuth();
  
  if (!user) return null;
  
  return (
    <div>
      <span style={{ marginRight: '10px' }}>{user.email || 'Moderator'}</span>
      <button
        className="btn btn-secondary"
        onClick={logout}
        style={{ padding: '4px 12px', fontSize: '14px' }}
      >
        Logout
      </button>
    </div>
  );
}

export default App;

