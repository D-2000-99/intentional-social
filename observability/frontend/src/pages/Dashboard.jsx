import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import ReportedPostCard from "../components/ReportedPostCard";
import UserList from "../components/UserList";

export default function Dashboard() {
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState("reports");
    const [reports, setReports] = useState([]);
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [usersLoading, setUsersLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        if (activeTab === "reports") {
            loadReports();
        } else {
            loadUsers();
        }
    }, [activeTab, token]);

    const loadReports = async () => {
        setLoading(true);
        try {
            const data = await api.getReportedPosts(token, 0, 100, true);
            setReports(data);
        } catch (err) {
            alert(`Failed to load reports: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const loadUsers = async () => {
        setUsersLoading(true);
        try {
            const data = await api.getUsers(token, 0, 100, searchQuery || null);
            setUsers(data);
        } catch (err) {
            alert(`Failed to load users: ${err.message}`);
        } finally {
            setUsersLoading(false);
        }
    };

    const handleReportResolved = (reportId) => {
        setReports(reports.filter(r => r.id !== reportId));
    };

    const handlePostDeleted = (postId) => {
        // Remove reports that reference the deleted post
        setReports(reports.filter(r => r.post_id !== postId));
    };

    const handleUsersUpdate = () => {
        loadUsers();
    };

    const handleSearch = () => {
        loadUsers();
    };

    return (
        <div className="container">
            <div className="dashboard-tabs">
                <button
                    className={`tab-button ${activeTab === "reports" ? "active" : ""}`}
                    onClick={() => setActiveTab("reports")}
                >
                    Reported Posts
                </button>
                <button
                    className={`tab-button ${activeTab === "users" ? "active" : ""}`}
                    onClick={() => setActiveTab("users")}
                >
                    User Management
                </button>
            </div>

            {activeTab === "reports" && (
                <div>
                    <h2>Reported Posts</h2>
                    {loading ? (
                        <div className="loading">Loading reports...</div>
                    ) : reports.length === 0 ? (
                        <div className="loading">No reported posts</div>
                    ) : (
                        <div className="reported-posts-list">
                            {reports.map((report) => (
                                <ReportedPostCard
                                    key={report.id}
                                    report={report}
                                    onResolved={handleReportResolved}
                                    onPostDeleted={handlePostDeleted}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}

            {activeTab === "users" && (
                <div>
                    <h2>User Management</h2>
                    <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
                        <input
                            type="text"
                            placeholder="Search by email, username, or name..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                            style={{ padding: '8px', flex: 1, fontSize: '14px' }}
                        />
                        <button
                            className="btn btn-primary"
                            onClick={handleSearch}
                        >
                            Search
                        </button>
                    </div>
                    {usersLoading ? (
                        <div className="loading">Loading users...</div>
                    ) : users.length === 0 ? (
                        <div className="loading">No users found</div>
                    ) : (
                        <UserList users={users} onUpdate={handleUsersUpdate} />
                    )}
                </div>
            )}
        </div>
    );
}

