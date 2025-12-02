import { createContext, useState, useEffect, useContext } from "react";
import { jwtDecode } from "jwt-decode";
import { api } from "../api";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(localStorage.getItem("token"));
    const [user, setUser] = useState(null);

    useEffect(() => {
        if (token) {
            try {
                const decoded = jwtDecode(token);
                // Check expiry
                if (decoded.exp * 1000 < Date.now()) {
                    logout();
                } else {
                    // Fetch full user details from backend
                    fetchUserDetails();
                    localStorage.setItem("token", token);
                }
            } catch (e) {
                logout();
            }
        } else {
            localStorage.removeItem("token");
        }
    }, [token]);

    const fetchUserDetails = async () => {
        try {
            const userData = await api.request("/auth/me", "GET", null, token);
            setUser(userData);
        } catch (err) {
            console.error("Failed to fetch user details", err);
            logout();
        }
    };

    const login = (newToken) => {
        setToken(newToken);
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem("token");
    };

    return (
        <AuthContext.Provider value={{ token, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
