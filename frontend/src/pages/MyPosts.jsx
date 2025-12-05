import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function MyPosts() {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deletingPostId, setDeletingPostId] = useState(null);
    const { token } = useAuth();

    const fetchMyPosts = async () => {
        setLoading(true);
        try {
            const data = await api.getMyPosts(token);
            // Debug: log posts with photos
            data.forEach(post => {
                if (post.photo_urls && post.photo_urls.length > 0) {
                    console.log(`Post ${post.id} has ${post.photo_urls.length} photos:`, {
                        photo_urls: post.photo_urls,
                        photo_urls_presigned: post.photo_urls_presigned,
                        presigned_count: post.photo_urls_presigned?.length || 0
                    });
                }
            });
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

    const handleDeletePost = async (postId) => {
        // Confirm deletion
        const confirmed = window.confirm(
            "Are you sure you want to delete this post? This action cannot be undone."
        );
        
        if (!confirmed) {
            return;
        }

        setDeletingPostId(postId);
        try {
            await api.deletePost(token, postId);
            // Remove the post from the list
            setPosts(prevPosts => prevPosts.filter(post => post.id !== postId));
        } catch (err) {
            console.error("Failed to delete post", err);
            alert(`Failed to delete post: ${err.message}`);
        } finally {
            setDeletingPostId(null);
        }
    };

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
                                <button
                                    onClick={() => handleDeletePost(post.id)}
                                    disabled={deletingPostId === post.id}
                                    className="delete-post-button"
                                    title="Delete post"
                                >
                                    {deletingPostId === post.id ? "Deleting..." : "🗑️"}
                                </button>
                            </div>
                            {post.content && (
                                <p className="post-content">{post.content}</p>
                            )}
                            {/* Display photos */}
                            {post.photo_urls_presigned && post.photo_urls_presigned.length > 0 && (
                                <div className="post-photos">
                                    {post.photo_urls_presigned.map((url, index) => (
                                        <img
                                            key={index}
                                            src={url}
                                            alt={`Post photo ${index + 1}`}
                                            className="post-photo"
                                            loading="lazy"
                                            onError={(e) => {
                                                console.error(`Failed to load image ${index + 1} for post ${post.id}`);
                                                console.error(`Full URL:`, url);
                                                console.error(`Error details:`, e);
                                                e.target.style.display = 'none';
                                            }}
                                            onLoad={() => {
                                                console.log(`Successfully loaded image ${index + 1} for post ${post.id}`);
                                            }}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
