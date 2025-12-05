import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Search() {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const { token } = useAuth();

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError("");
        try {
            const data = await api.searchUsers(token, query.trim());
            setResults(data);
            if (data.length === 0) {
                setError("No users found with that exact username or email");
            }
        } catch (err) {
            setError(err.message);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const handleSendRequest = async (userId) => {
        try {
            await api.sendConnectionRequest(token, userId);
            alert("Connection request sent!");
            // Remove from results
            setResults(results.filter(u => u.id !== userId));
        } catch (err) {
            alert(err.message);
        }
    };

    return (
        <div className="search-container">
            <h2>Search Users</h2>
            <p className="search-hint">Search by exact username or email</p>

            <form onSubmit={handleSearch} className="search-form">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter username or email..."
                    className="search-input"
                    aria-label="Search users"
                />
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? "Searching..." : "Search"}
                </button>
            </form>

            {error && <p className="error">{error}</p>}

            {results.length > 0 && (
                <div className="search-results">
                    <h3>Results</h3>
                    <div className="user-list">
                        {results.map((user) => (
                            <div key={user.id} className="user-card">
                                <div className="user-info">
                                    <span className="username">@{user.username || 'N/A'}</span>
                                    <span className="email">{user.email}</span>
                                </div>
                                <button 
                                    onClick={() => handleSendRequest(user.id)}
                                    className="btn-primary"
                                    aria-label={`Send connection request to ${user.username || user.email}`}
                                >
                                    Send Request
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {!loading && query && results.length === 0 && !error && (
                <div className="empty-state">
                    <p>No users found with that exact username or email.</p>
                </div>
            )}
        </div>
    );
}
