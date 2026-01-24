import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PostCard from "../components/PostCard";

export default function MyPosts() {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deletingPostId, setDeletingPostId] = useState(null);
    const { token, user: currentUser } = useAuth();

    const fetchMyPosts = async () => {
        setLoading(true);
        try {
            const data = await api.getMyPosts(token);
            // Debug: log posts with photos
            data.forEach(post => {
                if (post.photo_urls && post.photo_urls.length > 0) {
                    console.log(`Post ${post.id} has ${post.photo_urls.length} photos:`, {
                        photo_urls: post.photo_urls,
                        photo_urls_access: post.photo_urls_presigned,
                        access_count: post.photo_urls_presigned?.length || 0
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

    if (loading) return <p className="loading-state">Loading...</p>;

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
                        <PostCard 
                            key={post.id} 
                            post={post} 
                            currentUser={currentUser}
                            showDeleteButton={true}
                            onPostDeleted={handleDeletePost}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
