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

    if (loading) return <p>Loading...</p>;

    return (
        <div className="requests-container">
            <section>
                <h2>Incoming Requests</h2>
                {incoming.length === 0 ? (
                    <p className="empty-state">No incoming requests</p>
                ) : (
                    <div className="user-list">
                        {incoming.map((req) => (
                            <div key={req.id} className="user-card">
                                <div className="user-info">
                                    <span className="username">@{req.other_user_username}</span>
                                    <span className="email">{req.other_user_email}</span>
                                    <span className="date">
                                        {new Date(req.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <div className="actions">
                                    <button onClick={() => handleAccept(req.id)}>Accept</button>
                                    <button
                                        className="secondary"
                                        onClick={() => handleReject(req.id)}
                                    >
                                        Reject
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            <section style={{ marginTop: "3rem" }}>
                <h2>Outgoing Requests</h2>
                {outgoing.length === 0 ? (
                    <p className="empty-state">No outgoing requests</p>
                ) : (
                    <div className="user-list">
                        {outgoing.map((req) => (
                            <div key={req.id} className="user-card">
                                <div className="user-info">
                                    <span className="username">@{req.other_user_username}</span>
                                    <span className="email">{req.other_user_email}</span>
                                    <span className="date">
                                        Sent {new Date(req.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <div className="actions">
                                    <button
                                        className="secondary"
                                        onClick={() => handleReject(req.id)}
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
