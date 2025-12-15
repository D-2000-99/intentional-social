import { useState, useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import TagPill from "../components/TagPill";
import TagPicker from "../components/TagPicker";
import ConnectionInsights from "../components/ConnectionInsights";

export default function Connections() {
    // Tab state
    const [activeTab, setActiveTab] = useState("circle");

    // Search state
    const [query, setQuery] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState("");
    const searchInputRef = useRef(null);

    // Requests state
    const [incoming, setIncoming] = useState([]);
    const [outgoing, setOutgoing] = useState([]);
    const [requestsLoading, setRequestsLoading] = useState(true);

    // Connections state
    const [connections, setConnections] = useState([]);
    const [connectionTags, setConnectionTags] = useState({});
    const [allTags, setAllTags] = useState([]);
    const [selectedTagFilter, setSelectedTagFilter] = useState(null);
    const [connectionsLoading, setConnectionsLoading] = useState(true);

    // Kebab menu state
    const [openKebabId, setOpenKebabId] = useState(null);

    const { token } = useAuth();

    // Auto-focus search input when Find People tab is clicked
    useEffect(() => {
        if (activeTab === "find" && searchInputRef.current) {
            searchInputRef.current.focus();
        }
    }, [activeTab]);

    // Close kebab menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (!event.target.closest('.kebab-menu-container')) {
                setOpenKebabId(null);
            }
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    // Search functionality
    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearchLoading(true);
        setSearchError("");
        try {
            const data = await api.searchUsers(token, query.trim());
            setSearchResults(data);
            if (data.length === 0) {
                setSearchError("No users found with that exact username or email");
            }
        } catch (err) {
            setSearchError(err.message);
            setSearchResults([]);
        } finally {
            setSearchLoading(false);
        }
    };

    const handleSendRequest = async (userId) => {
        try {
            await api.sendConnectionRequest(token, userId);
            alert("Connection request sent!");
            // Remove from results and refresh requests
            setSearchResults(searchResults.filter(u => u.id !== userId));
            fetchRequests();
        } catch (err) {
            alert(err.message);
        }
    };

    // Requests functionality
    const fetchRequests = async () => {
        setRequestsLoading(true);
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
            setRequestsLoading(false);
        }
    };

    const handleAccept = async (connectionId) => {
        try {
            await api.acceptRequest(token, connectionId);
            fetchRequests();
            fetchConnections(); // Refresh connections too
            alert("Connection accepted!");
        } catch (err) {
            alert(err.message);
        }
    };

    const handleReject = async (connectionId) => {
        try {
            await api.rejectRequest(token, connectionId);
            fetchRequests();
            alert("Request rejected");
        } catch (err) {
            alert(err.message);
        }
    };

    // Connections functionality
    const fetchConnections = async () => {
        setConnectionsLoading(true);
        try {
            const data = await api.getConnections(token);
            setConnections(data);

            // Ensure user tags are loaded for filtering
            let userTags = allTags;
            if (userTags.length === 0) {
                userTags = await api.getTags(token);
                setAllTags(userTags);
            }
            
            // Fetch tags for each connection
            const tagsMap = {};
            const userTagIds = new Set(userTags.map(t => t.id));
            
            for (const conn of data) {
                try {
                    const tags = await api.getConnectionTags(token, conn.id);
                    const filteredTags = tags.filter(tag => userTagIds.has(tag.id));
                    tagsMap[conn.id] = filteredTags;
                } catch (err) {
                    tagsMap[conn.id] = [];
                }
            }
            setConnectionTags(tagsMap);
        } catch (err) {
            console.error("Failed to fetch connections", err);
        } finally {
            setConnectionsLoading(false);
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
            return connections;
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

    const handleDisconnect = async (connectionId, username) => {
        setOpenKebabId(null);
        if (!confirm(`Are you sure you want to disconnect from @${username}?`)) {
            return;
        }

        try {
            await api.disconnect(token, connectionId);
            fetchConnections();
            alert("Disconnected successfully");
        } catch (err) {
            alert(err.message);
        }
    };

    const handleEditTag = (connectionId) => {
        setOpenKebabId(null);
        // Tag editing is handled inline with TagPicker component
        // This function can be used to trigger focus or highlight
    };

    useEffect(() => {
        fetchTags();
        fetchRequests();
        fetchConnections();
    }, [token]);

    const renderConnectionCard = (conn) => {
        const tags = connectionTags[conn.id] || [];
        const primaryTag = tags[0]; // Show first tag as "Friend Tag"
        
        return (
        <div key={conn.id} className="user-card">
            <div className="user-info">
                    <div className="connection-row-main">
                        <div className="connection-avatar-name">
                            {/* Avatar placeholder - you may want to add actual avatar support */}
                            <div className="connection-avatar">
                                {conn.other_user_username?.charAt(0).toUpperCase() || '?'}
                            </div>
                            <div className="connection-name-group">
                <Link 
                    to={`/profile/${conn.other_user_username}`}
                    className="username username-link"
                >
                                    {conn.other_user_email?.split('@')[0] || conn.other_user_username || 'Unknown'}
                </Link>
                                <span className="username-secondary">@{conn.other_user_username}</span>
                            </div>
                        </div>
                        {primaryTag && (
                            <TagPill tag={primaryTag} />
                        )}
                    </div>

                <div className="connection-tags">
                        {tags.map((tag) => (
                        <TagPill
                            key={tag.id}
                            tag={tag}
                            onRemove={(t) => handleRemoveTag(conn.id, t)}
                        />
                    ))}
                    <TagPicker
                        onTagSelect={(tag) => handleAddTag(conn.id, tag)}
                            existingTagIds={tags.map(t => t.id)}
                    />
                </div>
            </div>
                <div className="actions kebab-menu-container">
                    <button
                        className="kebab-menu-button"
                        onClick={(e) => {
                            e.stopPropagation();
                            setOpenKebabId(openKebabId === conn.id ? null : conn.id);
                        }}
                        aria-label="Connection options"
                    >
                        ⋮
                    </button>
                    {openKebabId === conn.id && (
                        <div className="kebab-menu-popover">
                            <button
                                className="kebab-menu-item"
                                onClick={() => handleEditTag(conn.id)}
                            >
                                Edit Tag
                            </button>
                <button
                                className="kebab-menu-item kebab-menu-item-danger"
                    onClick={() => handleDisconnect(conn.id, conn.other_user_username)}
                >
                    Disconnect
                </button>
                        </div>
                    )}
            </div>
        </div>
    );
    };

    const isLoading = requestsLoading || connectionsLoading;

    return (
        <div className="connections-unified-container">
            {/* Hero Section - Circle Capacity */}
            <div className="connections-hero">
                <ConnectionInsights />
            </div>

            {/* Tab System */}
            <div className="connections-tabs">
                <button
                    className={`connections-tab ${activeTab === "circle" ? "active" : ""}`}
                    onClick={() => setActiveTab("circle")}
                >
                    My Circle
                </button>
                <button
                    className={`connections-tab ${activeTab === "requests" ? "active" : ""}`}
                    onClick={() => setActiveTab("requests")}
                >
                    Requests
                    {incoming.length > 0 && (
                        <span className="tab-badge">{incoming.length}</span>
                    )}
                </button>
                <button
                    className={`connections-tab ${activeTab === "find" ? "active" : ""}`}
                    onClick={() => setActiveTab("find")}
                >
                    Find People
                </button>
            </div>

            {/* Tab 1: My Circle */}
            {activeTab === "circle" && (
                <section className="connections-section">
                    <div className="connections-header">
                        <h2 className="section-title">My Connections ({filteredConnections.length}{selectedTagFilter ? ` of ${connections.length}` : ''})</h2>
                        
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

                    {connectionsLoading ? (
                        <p className="loading-state">Loading connections...</p>
                    ) : connections.length === 0 ? (
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
                </section>
            )}

            {/* Tab 2: Requests */}
            {activeTab === "requests" && (
                <section className="connections-section">
                    {requestsLoading ? (
                        <p className="loading-state">Loading requests...</p>
                    ) : incoming.length === 0 && outgoing.length === 0 ? (
                        <div className="empty-state">
                            <p>No one is knocking at the door right now.</p>
                        </div>
                    ) : (
                        <>
                            {/* Incoming Requests */}
                            {incoming.length > 0 && (
                                <div className="requests-subsection">
                                    <h3 className="subsection-title">Incoming Requests ({incoming.length})</h3>
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
                                </div>
                            )}

                            {/* Outgoing Requests */}
                            {outgoing.length > 0 && (
                                <div className="requests-subsection">
                                    <h3 className="subsection-title">Outgoing Requests ({outgoing.length})</h3>
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
                                </div>
                            )}
                        </>
                    )}
                </section>
            )}

            {/* Tab 3: Find People */}
            {activeTab === "find" && (
            <section className="connections-section">
                <h2 className="section-title">Search Users</h2>
                <p className="search-hint">Search by exact username or email</p>

                <form onSubmit={handleSearch} className="search-form">
                    <input
                            ref={searchInputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Enter username or email..."
                        className="search-input"
                        aria-label="Search users"
                    />
                    <button type="submit" className="btn-primary" disabled={searchLoading}>
                        {searchLoading ? "Searching..." : "Search"}
                    </button>
                </form>

                {searchError && <p className="error">{searchError}</p>}

                {searchResults.length > 0 && (
                    <div className="search-results">
                        <h3 className="subsection-title">Results</h3>
                        <div className="user-list">
                            {searchResults.map((user) => (
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

                {!searchLoading && query && searchResults.length === 0 && !searchError && (
                    <div className="empty-state">
                        <p>No users found with that exact username or email.</p>
                    </div>
                )}
            </section>
            )}
        </div>
    );
}
