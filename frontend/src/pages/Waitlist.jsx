import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Waitlist() {
    const { user, logout, token } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);

    // If user is not waitlisted, redirect to home
    useEffect(() => {
        if (user) {
            setLoading(false);
            // Only redirect if user is explicitly not waitlisted
            if (user.needs_waitlist === false) {
                navigate("/", { replace: true });
            }
        } else if (token) {
            // User data is still loading, keep loading state
            setLoading(true);
        } else {
            // No token, redirect to login
            navigate("/login", { replace: true });
        }
    }, [user, token, navigate]);

    const handleLogout = () => {
        logout();
        navigate("/login", { replace: true });
    };

    // Show loading state while user data is being fetched
    if (loading || !user) {
        return (
            <div className="auth-container">
                <h1 className="serif-font">Intentional Social</h1>
                <div className="auth-loading">
                    <p>Loading...</p>
                </div>
            </div>
        );
    }

    // If user doesn't need waitlist, show loading while redirect happens
    if (user.needs_waitlist === false) {
        return (
            <div className="auth-container">
                <h1 className="serif-font">Intentional Social</h1>
                <div className="auth-loading">
                    <p>Redirecting...</p>
                </div>
            </div>
        );
    }

    // Render waitlist content - always show something even if user data is incomplete
    return (
        <div className="auth-container" style={{ maxWidth: "600px" }}>
            <h1 className="serif-font">We're Scaling Soon!</h1>
            <div style={{ 
                backgroundColor: "white", 
                padding: "32px", 
                borderRadius: "8px", 
                boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
                textAlign: "center",
                marginTop: "20px",
                width: "100%",
                boxSizing: "border-box"
            }}>
                <p style={{ color: "#666", marginBottom: "24px", lineHeight: "1.6", fontSize: "16px" }}>
                    Thank you for your interest in Intentional Social! We're currently in our MVP phase 
                    and working on scaling our platform to welcome more users.
                </p>
                <p style={{ color: "#666", marginBottom: "24px", lineHeight: "1.6", fontSize: "16px" }}>
                    Your account has been created successfully. We'll notify you as soon as we're ready 
                    to expand access. We appreciate your patience!
                </p>
                
                {user?.email && (
                    <p style={{ 
                        marginBottom: "24px", 
                        padding: "12px",
                        backgroundColor: "#f5f5f5",
                        borderRadius: "4px",
                        fontSize: "14px"
                    }}>
                        <strong>Registered email:</strong> {user.email}
                    </p>
                )}
                
                <button
                    onClick={handleLogout}
                    style={{
                        padding: "12px 24px",
                        border: "none",
                        borderRadius: "4px",
                        backgroundColor: "#1976d2",
                        color: "white",
                        cursor: "pointer",
                        fontSize: "16px",
                        fontWeight: "500",
                    }}
                >
                    Sign Out
                </button>
            </div>
        </div>
    );
}
