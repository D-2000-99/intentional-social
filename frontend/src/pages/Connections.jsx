import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Connections() {
    const [connections, setConnections] = useState([]);
    const [loading, setLoading] = useState(true);
    const { token } = useAuth();

    const fetchConnections = async () => {
        setLoading(true);
        try {
            const data = await api.getConnections(token);
            setConnections(data);
        } catch (err) {
            console.error("Failed to fetch connections", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConnections();
    }, [token]);

    const handleDisconnect = async (connectionId, username) => {
        if (!confirm(`Are you sure you want to disconnect from @${username}?`)) {
            return;
        }

        try {
            await api.disconnect(token, connectionId);
            fetchConnections(); // Refresh
            alert("Disconnected successfully");
        } catch (err) {
            alert(err.message);
        }
    };

    if (loading) return <p>Loading...</p>;

    return (
        <div className="connections-container">
            <h2>My Connections ({connections.length})</h2>

            {connections.length === 0 ? (
                <div className="empty-state">
                    <p>You don't have any connections yet.</p>
                    <p>Search for users to send connection requests.</p>
                </div>
            ) : (
                <div className="user-list">
                    {connections.map((conn) => (
                        <div key={conn.id} className="user-card">
                            <div className="user-info">
                                <span className="username">@{conn.other_user_username}</span>
                                <span className="email">{conn.other_user_email}</span>
                                <span className="date">
                                    Connected {new Date(conn.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <div className="actions">
                                <button
                                    className="secondary"
                                    onClick={() => handleDisconnect(conn.id, conn.other_user_username)}
                                >
                                    Disconnect
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
