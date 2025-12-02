import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Feed() {
    const [posts, setPosts] = useState([]);
    const [content, setContent] = useState("");
    const [loading, setLoading] = useState(true);
    const { token } = useAuth();

    const fetchFeed = async () => {
        try {
            const data = await api.getFeed(token);
            setPosts(data);
        } catch (err) {
            console.error("Failed to fetch feed", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFeed();
    }, [token]);

    const handlePost = async (e) => {
        e.preventDefault();
        if (!content.trim()) return;

        try {
            await api.createPost(token, content);
            setContent("");
            fetchFeed(); // Refresh feed
        } catch (err) {
            alert("Failed to post");
        }
    };

    return (
        <div className="feed-container">
            <div className="create-post">
                <form onSubmit={handlePost}>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="What's on your mind?"
                        rows="3"
                    />
                    <div className="post-actions">
                        <button type="submit" disabled={!content.trim()}>
                            Post
                        </button>
                    </div>
                </form>
            </div>

            <div className="feed-list">
                {loading ? (
                    <p>Loading...</p>
                ) : posts.length === 0 ? (
                    <div className="empty-state">
                        <p>Your feed is quiet.</p>
                        <p>Follow people to see their thoughts here.</p>
                    </div>
                ) : (
                    posts.map((post) => (
                        <div key={post.id} className="post-card">
                            <div className="post-header">
                                <span className="author">@{post.author.username}</span>
                                <span className="date">
                                    {new Date(post.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <p className="post-content">{post.content}</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
