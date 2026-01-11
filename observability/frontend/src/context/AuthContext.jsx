import { createContext, useContext, useState, useEffect } from "react";
import { jwtDecode } from "jwt-decode";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setUser({ id: decoded.sub, ...decoded });
      } catch (error) {
        console.error("Failed to decode token:", error);
        setToken(null);
        localStorage.removeItem("token");
      }
    }
    setLoading(false);
  }, [token]);

  const login = (newToken) => {
    setToken(newToken);
    localStorage.setItem("token", newToken);
    try {
      const decoded = jwtDecode(newToken);
      setUser({ id: decoded.sub, ...decoded });
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("token");
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

