import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import TagPill from "../components/TagPill";
import TagPicker from "../components/TagPicker";

export default function Connections() {
    const [connections, setConnections] = useState([]);
    const [connectionTags, setConnectionTags] = useState({});
    const [allTags, setAllTags] = useState([]);
    const [selectedTagFilter, setSelectedTagFilter] = useState(null); // null means "all"
    const [loading, setLoading] = useState(true);
    const { token } = useAuth();

    const fetchConnections = async () => {
        setLoading(true);
        try {
            const data = await api.getConnections(token);
            setConnections(data);

            // Fetch tags for each connection
            const tagsMap = {};
            for (const conn of data) {
                try {
                    const tags = await api.getConnectionTags(token, conn.id);
                    tagsMap[conn.id] = tags;
                } catch (err) {
                    tagsMap[conn.id] = [];
                }
            }
            setConnectionTags(tagsMap);
        } catch (err) {
            console.error("Failed to fetch connections", err);
        } finally {
            setLoading(false);
        }
    };

    const fetchTags = async () => {
        try {
            const tags = await api.getTags(token);
            setAllTags(tags);
        } catch (err) {
            console.error("Failed to fetch tags", err);
        }
    };

    // Filter connections based on selected tag
    const filteredConnections = useMemo(() => {
        if (!selectedTagFilter) {
            return connections; // Show all connections
        }

        return connections.filter(conn => {
            const tags = connectionTags[conn.id] || [];
            return tags.some(tag => tag.id === selectedTagFilter);
        });
    }, [connections, connectionTags, selectedTagFilter]);

    const handleAddTag = async (connectionId, tag) => {
        try {
            await api.addTagToConnection(token, connectionId, tag.id);
            setConnectionTags({
                ...connectionTags,
                [connectionId]: [...(connectionTags[connectionId] || []), tag],
            });
        } catch (err) {
            alert(err.message);
        }
    };

    const handleRemoveTag = async (connectionId, tag) => {
        try {
            await api.removeTagFromConnection(token, connectionId, tag.id);
            setConnectionTags({
                ...connectionTags,
                [connectionId]: connectionTags[connectionId].filter(t => t.id !== tag.id),
            });
        } catch (err) {
            alert(err.message);
        }
    };

    useEffect(() => {
        fetchConnections();
        fetchTags();
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

    const renderConnectionCard = (conn) => (
        <div key={conn.id} className="user-card">
            <div className="user-info">
                <Link 
                    to={`/profile/${conn.other_user_username}`}
                    className="username username-link"
                >
                    @{conn.other_user_username}
                </Link>
                <span className="email">{conn.other_user_email}</span>
                <span className="date">
                    Connected {new Date(conn.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>

                <div className="connection-tags">
                    {(connectionTags[conn.id] || []).map((tag) => (
                        <TagPill
                            key={tag.id}
                            tag={tag}
                            onRemove={(t) => handleRemoveTag(conn.id, t)}
                        />
                    ))}
                    <TagPicker
                        onTagSelect={(tag) => handleAddTag(conn.id, tag)}
                        existingTagIds={(connectionTags[conn.id] || []).map(t => t.id)}
                    />
                </div>
            </div>
            <div className="actions">
                <button
                    className="secondary"
                    onClick={() => handleDisconnect(conn.id, conn.other_user_username)}
                    aria-label={`Disconnect from ${conn.other_user_username}`}
                >
                    Disconnect
                </button>
            </div>
        </div>
    );

    if (loading) return <p className="loading-state">Loading...</p>;

    return (
        <div className="connections-container">
            <div className="connections-header">
                <h2>My Connections ({filteredConnections.length}{selectedTagFilter ? ` of ${connections.length}` : ''})</h2>
                
                {/* Tag Filter */}
                <div className="tag-filter-container">
                    <label htmlFor="tag-filter" className="tag-filter-label">Filter by tag:</label>
                    <select
                        id="tag-filter"
                        className="tag-filter-select"
                        value={selectedTagFilter || ''}
                        onChange={(e) => setSelectedTagFilter(e.target.value ? parseInt(e.target.value) : null)}
                    >
                        <option value="">All Connections</option>
                        {allTags.map(tag => (
                            <option key={tag.id} value={tag.id}>
                                {tag.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {connections.length === 0 ? (
                <div className="empty-state">
                    <p>You don't have any connections yet.</p>
                    <p>Search for users to send connection requests.</p>
                </div>
            ) : filteredConnections.length === 0 ? (
                <div className="empty-state">
                    <p>No connections found with the selected tag filter.</p>
                </div>
            ) : (
                <div className="user-list">
                    {filteredConnections.map(conn => renderConnectionCard(conn))}
                </div>
            )}
        </div>
    );
}
