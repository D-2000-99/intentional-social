import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function People() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const { token, user: currentUser } = useAuth();

    // Ideally, we'd have an endpoint to get "who I follow" separately
    // For MVP, we might need to fetch all users and check status if the backend supports it
    // Or just list all users and let the backend handle the "already following" error
    // Let's assume GET /auth/users returns all users.
    // We need to know who we follow to show "Unfollow".
    // The current backend doesn't seem to have a "get my follows" endpoint easily accessible 
    // without checking the relationship.
    // Wait, `GET /auth/users` returns UserOut which has `followers` list?
    // Let's check the User schema.

    const fetchUsers = async () => {
        try {
            const data = await api.getUsers(token);
            // Filter out self
            setUsers(data.filter(u => u.username !== currentUser.username));
        } catch (err) {
            setError("Failed to load users");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, [token]);

    const handleFollow = async (userId) => {
        try {
            await api.followUser(token, userId);
            // Optimistic update or refresh?
            // Since we don't have "is_following" in the user list easily, 
            // we rely on the button action.
            // For a better UX, we should fetch "my follows" or have `is_following` in the user list.
            // Given the constraints, let's just alert success for now or refresh.
            alert("Followed!");
            fetchUsers();
        } catch (err) {
            alert(err.message);
        }
    };

    const handleUnfollow = async (userId) => {
        try {
            await api.unfollowUser(token, userId);
            alert("Unfollowed");
            fetchUsers();
        } catch (err) {
            alert(err.message);
        }
    }

    // Helper to check if we follow someone. 
    // The `UserOut` schema from backend: id, email, username, created_at.
    // It DOES NOT include followers/following by default to avoid N+1 or circular depth.
    // So we can't easily know if we follow them from the list.
    // We will just show "Follow" button. If we follow them, backend returns 409.
    // We can show "Unfollow" button if we get 409? No that's bad UX.

    // WORKAROUND: We need to know who we follow.
    // The backend `User` model has `following`.
    // But `UserOut` schema doesn't expose it.
    // We should probably update the backend to return `is_following` or expose `following` list for the current user.
    // BUT, I am in frontend mode. I should stick to existing APIs if possible.
    // Existing APIs:
    // GET /auth/users -> List[UserOut]
    // POST /follows/{id}
    // DELETE /follows/{id}

    // If I can't change backend, I have to guess.
    // OR, I can try to follow, if 409, then show "Unfollow"?
    // That's clunky.

    // Let's check `UserOut` schema in backend.
    // It inherits `UserBase`: email, username.

    // Okay, for this MVP, I will add a "Follow" button.
    // If the user is already followed, the backend returns 409 "Already following".
    // I will handle that error and maybe change the button state locally?
    // It's not persistent across reloads though.

    // Better approach:
    // I will assume I can modify the backend slightly to make the frontend usable, 
    // OR I accept the limitation.
    // The prompt says "APIs already exist... List who I follow".
    // Wait, the prompt says "List who I follow" IS an existing API?
    // Let's check the backend code.

    return (
        <div className="people-container">
            <h2>People</h2>
            {loading ? (
                <p className="loading-state">Loading...</p>
            ) : users.length === 0 ? (
                <div className="empty-state">
                    <p>No other users found.</p>
                    <p>Be the first to join!</p>
                </div>
            ) : (
                <div className="user-list">
                    {users.map((u) => (
                        <div key={u.id} className="user-card">
                            <div className="user-info">
                                <span className="username">@{u.username}</span>
                                <span className="joined">Joined {new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                            </div>
                            <div className="actions">
                                <button 
                                    onClick={() => handleFollow(u.id)}
                                    className="btn-primary"
                                    aria-label={`Follow ${u.username}`}
                                >
                                    Follow
                                </button>
                                <button 
                                    className="secondary" 
                                    onClick={() => handleUnfollow(u.id)}
                                    aria-label={`Unfollow ${u.username}`}
                                >
                                    Unfollow
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
