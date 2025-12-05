import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Requests() {
    const [incoming, setIncoming] = useState([]);
    const [outgoing, setOutgoing] = useState([]);
    const [loading, setLoading] = useState(true);
    const { token } = useAuth();

    const fetchRequests = async () => {
        setLoading(true);
        try {
            const [incomingData, outgoingData] = await Promise.all([
                api.getIncomingRequests(token),
                api.getOutgoingRequests(token),
            ]);
            setIncoming(incomingData);
            setOutgoing(outgoingData);
        } catch (err) {
            console.error("Failed to fetch requests", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, [token]);

    const handleAccept = async (connectionId) => {
        try {
            await api.acceptRequest(token, connectionId);
            fetchRequests(); // Refresh
            alert("Connection accepted!");
        } catch (err) {
            alert(err.message);
        }
    };

    const handleReject = async (connectionId) => {
        try {
            await api.rejectRequest(token, connectionId);
            fetchRequests(); // Refresh
            alert("Request rejected");
        } catch (err) {
            alert(err.message);
        }
    };

    if (loading) return <p className="loading-state">Loading...</p>;

    return (
        <div className="requests-container">
            <section>
                <h2>Incoming Requests</h2>
                {incoming.length === 0 ? (
                    <div className="empty-state">
                        <p>No incoming requests</p>
                    </div>
                ) : (
                    <div className="user-list">
                        {incoming.map((req) => (
                            <div key={req.id} className="user-card">
                                <div className="user-info">
                                    <span className="username">@{req.other_user_username}</span>
                                    <span className="email">{req.other_user_email}</span>
                                    <span className="date">
                                        {new Date(req.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                    </span>
                                </div>
                                <div className="actions">
                                    <button 
                                        onClick={() => handleAccept(req.id)}
                                        className="btn-primary"
                                        aria-label={`Accept request from ${req.other_user_username}`}
                                    >
                                        Accept
                                    </button>
                                    <button
                                        className="secondary"
                                        onClick={() => handleReject(req.id)}
                                        aria-label={`Reject request from ${req.other_user_username}`}
                                    >
                                        Reject
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            <section className="requests-section">
                <h2>Outgoing Requests</h2>
                {outgoing.length === 0 ? (
                    <div className="empty-state">
                        <p>No outgoing requests</p>
                    </div>
                ) : (
                    <div className="user-list">
                        {outgoing.map((req) => (
                            <div key={req.id} className="user-card">
                                <div className="user-info">
                                    <span className="username">@{req.other_user_username}</span>
                                    <span className="email">{req.other_user_email}</span>
                                    <span className="date">
                                        Sent {new Date(req.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                    </span>
                                </div>
                                <div className="actions">
                                    <button
                                        className="secondary"
                                        onClick={() => handleReject(req.id)}
                                        aria-label={`Cancel request to ${req.other_user_username}`}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
