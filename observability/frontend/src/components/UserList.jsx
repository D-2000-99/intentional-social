import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import UserActions from "./UserActions";

export default function UserList({ users, onUpdate }) {
    const { token } = useAuth();
    const [banningUserId, setBanningUserId] = useState(null);
    const [unbanningUserId, setUnbanningUserId] = useState(null);
    const [deletingUserId, setDeletingUserId] = useState(null);

    const handleBan = async (userId) => {
        setBanningUserId(userId);
        try {
            await api.banUser(token, userId);
            alert("User banned successfully");
            if (onUpdate) onUpdate();
        } catch (err) {
            alert(`Failed to ban user: ${err.message}`);
        } finally {
            setBanningUserId(null);
        }
    };

    const handleUnban = async (userId) => {
        setUnbanningUserId(userId);
        try {
            await api.unbanUser(token, userId);
            alert("User unbanned successfully");
            if (onUpdate) onUpdate();
        } catch (err) {
            alert(`Failed to unban user: ${err.message}`);
        } finally {
            setUnbanningUserId(null);
        }
    };

    const handleDelete = async (userId) => {
        if (!confirm(`Are you sure you want to delete this user? This action cannot be undone and will delete all their posts, comments, and data.`)) {
            return;
        }
        
        if (!confirm("This is your final warning. Delete this user and all associated data?")) {
            return;
        }
        
        setDeletingUserId(userId);
        try {
            await api.deleteUser(token, userId);
            alert("User deleted successfully");
            if (onUpdate) onUpdate();
        } catch (err) {
            alert(`Failed to delete user: ${err.message}`);
        } finally {
            setDeletingUserId(null);
        }
    };

    return (
        <div className="users-table">
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Username</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {users.map((user) => (
                        <tr key={user.id}>
                            <td>{user.email}</td>
                            <td>{user.username || "—"}</td>
                            <td>
                                <span className={`status-badge ${user.is_banned ? 'banned' : 'active'}`}>
                                    {user.is_banned ? "Banned" : "Active"}
                                </span>
                            </td>
                            <td>{new Date(user.created_at).toLocaleDateString()}</td>
                            <td>
                                <UserActions
                                    user={user}
                                    onBan={() => handleBan(user.id)}
                                    onUnban={() => handleUnban(user.id)}
                                    onDelete={() => handleDelete(user.id)}
                                    banning={banningUserId === user.id}
                                    unbanning={unbanningUserId === user.id}
                                    deleting={deletingUserId === user.id}
                                />
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

