import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import ReportedPostCard from "../components/ReportedPostCard";
import UserList from "../components/UserList";
// MVP TEMPORARY: Registration Request component - Remove when moving beyond MVP
import RegistrationRequestList from "../components/RegistrationRequestList";

export default function Dashboard() {
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState("reports");
    const [reports, setReports] = useState([]);
    const [users, setUsers] = useState([]);
    // MVP TEMPORARY: Registration requests state - Remove when moving beyond MVP
    const [registrationRequests, setRegistrationRequests] = useState([]);
    const [loading, setLoading] = useState(true);
    const [usersLoading, setUsersLoading] = useState(false);
    const [requestsLoading, setRequestsLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState("pending"); // Filter for registration requests

    useEffect(() => {
        if (activeTab === "reports") {
            loadReports();
        } else if (activeTab === "users") {
            loadUsers();
        } else if (activeTab === "registration-requests") {
            // MVP TEMPORARY: Load registration requests - Remove when moving beyond MVP
            loadRegistrationRequests();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab, token, statusFilter]);

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

    // MVP TEMPORARY: Registration request loading function - Remove when moving beyond MVP
    const loadRegistrationRequests = async () => {
        setRequestsLoading(true);
        try {
            const data = await api.getRegistrationRequests(token, 0, 100, statusFilter || null);
            setRegistrationRequests(data);
        } catch (err) {
            alert(`Failed to load registration requests: ${err.message}`);
        } finally {
            setRequestsLoading(false);
        }
    };

    const handleRequestsUpdate = () => {
        loadRegistrationRequests();
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
                {/* MVP TEMPORARY: Registration Requests tab - Remove when moving beyond MVP */}
                <button
                    className={`tab-button ${activeTab === "registration-requests" ? "active" : ""}`}
                    onClick={() => setActiveTab("registration-requests")}
                >
                    Registration Requests
                    {registrationRequests.filter(r => r.status === "pending").length > 0 && (
                        <span style={{ 
                            marginLeft: "8px", 
                            backgroundColor: "#1976d2", 
                            color: "white", 
                            borderRadius: "10px", 
                            padding: "2px 6px", 
                            fontSize: "12px" 
                        }}>
                            {registrationRequests.filter(r => r.status === "pending").length}
                        </span>
                    )}
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

            {/* MVP TEMPORARY: Registration Requests tab content - Remove when moving beyond MVP */}
            {activeTab === "registration-requests" && (
                <div>
                    <h2>Registration Requests</h2>
                    <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <label style={{ fontSize: '14px' }}>Filter by status:</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => {
                                setStatusFilter(e.target.value);
                            }}
                            style={{ padding: '8px', fontSize: '14px', minWidth: '150px' }}
                        >
                            <option value="">All</option>
                            <option value="pending">Pending</option>
                            <option value="approved">Approved</option>
                            <option value="denied">Denied</option>
                        </select>
                        <button
                            className="btn btn-primary"
                            onClick={loadRegistrationRequests}
                            style={{ marginLeft: 'auto' }}
                        >
                            Refresh
                        </button>
                    </div>
                    {requestsLoading ? (
                        <div className="loading">Loading registration requests...</div>
                    ) : registrationRequests.length === 0 ? (
                        <div className="loading">No registration requests found</div>
                    ) : (
                        <RegistrationRequestList 
                            requests={registrationRequests} 
                            onUpdate={handleRequestsUpdate} 
                        />
                    )}
                </div>
            )}
        </div>
    );
}

