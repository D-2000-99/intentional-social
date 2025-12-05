import { useState } from "react";

export default function UsernameSelectionModal({ user, onUsernameSelected, onCancel }) {
    const [username, setUsername] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        
        // Basic validation
        if (!username || username.length < 3) {
            setError("Username must be at least 3 characters long");
            return;
        }
        
        if (username.length > 50) {
            setError("Username must be at most 50 characters long");
            return;
        }
        
        // Check for valid characters (letters, numbers, underscores, hyphens)
        if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
            setError("Username can only contain letters, numbers, underscores, and hyphens");
            return;
        }
        
        setLoading(true);
        try {
            await onUsernameSelected(username.toLowerCase());
        } catch (err) {
            setError(err.message || "Failed to set username");
            setLoading(false);
        }
    };

    return (
        <div
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(0, 0, 0, 0.5)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1000,
            }}
            onClick={onCancel}
        >
            <div
                style={{
                    backgroundColor: "white",
                    padding: "24px",
                    borderRadius: "8px",
                    maxWidth: "400px",
                    width: "90%",
                    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <h2 style={{ marginTop: 0 }}>Choose Your Username</h2>
                <p style={{ color: "#666", marginBottom: "20px" }}>
                    Welcome! Please choose a username for your account.
                </p>
                
                {user?.full_name && (
                    <p style={{ marginBottom: "10px" }}>
                        <strong>Name:</strong> {user.full_name}
                    </p>
                )}
                
                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: "16px" }}>
                        <label style={{ display: "block", marginBottom: "8px", fontWeight: "500" }}>
                            Username
                        </label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => {
                                setUsername(e.target.value);
                                setError("");
                            }}
                            placeholder="username"
                            required
                            autoFocus
                            style={{
                                width: "100%",
                                padding: "10px",
                                fontSize: "16px",
                                border: "1px solid #ddd",
                                borderRadius: "4px",
                                boxSizing: "border-box",
                            }}
                        />
                        <p style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
                            3-50 characters, letters, numbers, underscores, and hyphens only
                        </p>
                    </div>
                    
                    {error && (
                        <p style={{ color: "#d32f2f", marginBottom: "16px", fontSize: "14px" }}>
                            {error}
                        </p>
                    )}
                    
                    <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
                        <button
                            type="button"
                            onClick={onCancel}
                            style={{
                                padding: "10px 20px",
                                border: "1px solid #ddd",
                                borderRadius: "4px",
                                backgroundColor: "white",
                                cursor: "pointer",
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            style={{
                                padding: "10px 20px",
                                border: "none",
                                borderRadius: "4px",
                                backgroundColor: "#1976d2",
                                color: "white",
                                cursor: loading ? "not-allowed" : "pointer",
                                opacity: loading ? 0.6 : 1,
                            }}
                        >
                            {loading ? "Setting..." : "Continue"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
