import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function MyPosts() {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const { token } = useAuth();

    const fetchMyPosts = async () => {
        setLoading(true);
        try {
            const data = await api.getMyPosts(token);
            setPosts(data);
        } catch (err) {
            console.error("Failed to fetch posts", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMyPosts();
    }, [token]);

    if (loading) return <p>Loading...</p>;

    return (
        <div className="my-posts-container">
            <h2>My Posts ({posts.length})</h2>

            {posts.length === 0 ? (
                <div className="empty-state">
                    <p>You haven't posted anything yet.</p>
                    <p>Go to the Feed to create your first post!</p>
                </div>
            ) : (
                <div className="feed-list">
                    {posts.map((post) => (
                        <div key={post.id} className="post-card">
                            <div className="post-header">
                                <span className="author">@{post.author.username}</span>
                                <span className="date">
                                    {new Date(post.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <p className="post-content">{post.content}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
