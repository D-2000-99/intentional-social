/**
 * Registration Request List Component - MVP TEMPORARY FEATURE
 * ===========================================================
 * This component displays and manages user registration requests during the MVP phase.
 * 
 * TODO: Remove this component when moving beyond MVP phase.
 * See observability/frontend/src/pages/Dashboard.jsx for the tab that uses this component.
 */
import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function RegistrationRequestList({ requests, onUpdate }) {
    const { token } = useAuth();
    const [approvingId, setApprovingId] = useState(null);
    const [denyingId, setDenyingId] = useState(null);

    const handleApprove = async (requestId) => {
        if (!confirm(`Approve this registration request? The user will be able to sign in immediately.`)) {
            return;
        }
        
        setApprovingId(requestId);
        try {
            await api.approveRegistrationRequest(token, requestId);
            alert("Registration request approved successfully");
            if (onUpdate) onUpdate();
        } catch (err) {
            alert(`Failed to approve request: ${err.message}`);
        } finally {
            setApprovingId(null);
        }
    };

    const handleDeny = async (requestId) => {
        if (!confirm(`Deny this registration request? The user will not be able to sign in.`)) {
            return;
        }
        
        setDenyingId(requestId);
        try {
            await api.denyRegistrationRequest(token, requestId);
            alert("Registration request denied");
            if (onUpdate) onUpdate();
        } catch (err) {
            alert(`Failed to deny request: ${err.message}`);
        } finally {
            setDenyingId(null);
        }
    };

    const getStatusBadge = (status) => {
        const statusClass = {
            pending: "status-badge pending",
            approved: "status-badge approved",
            denied: "status-badge denied"
        }[status] || "status-badge";
        
        const statusText = {
            pending: "Pending",
            approved: "Approved",
            denied: "Denied"
        }[status] || status;
        
        return <span className={statusClass}>{statusText}</span>;
    };

    return (
        <div className="registration-requests-table">
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Requested</th>
                        <th>Reviewed By</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {requests.map((request) => (
                        <tr key={request.id}>
                            <td>{request.email}</td>
                            <td>{request.full_name || "—"}</td>
                            <td>{getStatusBadge(request.status)}</td>
                            <td>{new Date(request.created_at).toLocaleDateString()}</td>
                            <td>
                                {request.reviewed_by ? (
                                    <span>{request.reviewed_by.email}</span>
                                ) : (
                                    <span>—</span>
                                )}
                            </td>
                            <td>
                                {request.status === "pending" && (
                                    <div style={{ display: "flex", gap: "8px" }}>
                                        <button
                                            className="btn btn-primary"
                                            onClick={() => handleApprove(request.id)}
                                            disabled={approvingId === request.id || denyingId === request.id}
                                            style={{ fontSize: "12px", padding: "6px 12px" }}
                                        >
                                            {approvingId === request.id ? "Approving..." : "Approve"}
                                        </button>
                                        <button
                                            className="btn btn-danger"
                                            onClick={() => handleDeny(request.id)}
                                            disabled={approvingId === request.id || denyingId === request.id}
                                            style={{ fontSize: "12px", padding: "6px 12px" }}
                                        >
                                            {denyingId === request.id ? "Denying..." : "Deny"}
                                        </button>
                                    </div>
                                )}
                                {request.status !== "pending" && (
                                    <span style={{ color: "#666", fontSize: "12px" }}>
                                        {request.status === "approved" ? "✓ Approved" : "✗ Denied"}
                                    </span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
