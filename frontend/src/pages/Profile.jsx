import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import imageCompression from "browser-image-compression";
import ConnectionInsights from "../components/ConnectionInsights";

export default function Profile() {
    const { username: urlUsername } = useParams();
    const navigate = useNavigate();
    const { user: currentUser, token, logout, refreshUser } = useAuth();
    const [profileUser, setProfileUser] = useState(null);
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [deletingPostId, setDeletingPostId] = useState(null);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    const isOwnProfile = !urlUsername || urlUsername === currentUser?.username;

    useEffect(() => {
        const fetchProfile = async () => {
            setLoading(true);
            try {
                if (isOwnProfile) {
                    // Viewing own profile
                    setProfileUser(currentUser);
                } else {
                    // Viewing another user's profile
                    const userData = await api.getUserByUsername(token, urlUsername);
                    setProfileUser(userData);
                }
            } catch (err) {
                console.error("Failed to fetch profile", err);
                setError(err.message || "Failed to load profile");
            } finally {
                setLoading(false);
            }
        };

        if (currentUser) {
            fetchProfile();
        }
    }, [urlUsername, currentUser, token, isOwnProfile]);

    useEffect(() => {
        const fetchPosts = async () => {
            if (!profileUser) return;
            
            try {
                const userPosts = await api.getUserPosts(token, profileUser.id);
                setPosts(userPosts);
            } catch (err) {
                console.error("Failed to fetch posts", err);
            }
        };

        if (profileUser) {
            fetchPosts();
        }
    }, [profileUser, token]);

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

    // Get avatar URL - prefer avatar_url (user-uploaded) over picture_url (Google)
    // The backend should return presigned URLs for S3 avatars
    const getAvatarUrl = () => {
        if (profileUser?.avatar_url) {
            return profileUser.avatar_url;
        }
        return profileUser?.picture_url || null;
    };

    const compressImage = async (file) => {
        const options = {
            maxSizeMB: 0.2, // 200KB
            maxWidthOrHeight: 720, // 720p
            useWebWorker: true,
            fileType: file.type,
        };
        
        try {
            const compressedFile = await imageCompression(file, options);
            return compressedFile;
        } catch (error) {
            console.error("Image compression error:", error);
            throw new Error("Failed to compress image");
        }
    };

    const handleAvatarChange = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            setError("Please select an image file");
            return;
        }

        setUploading(true);
        setError(null);

        try {
            const compressedFile = await compressImage(file);
            const updatedUser = await api.updateAvatar(token, compressedFile);
            
            // Refresh user data from backend to get updated presigned URL
            await refreshUser();
        } catch (err) {
            setError(err.message || "Failed to update avatar");
            console.error("Failed to update avatar", err);
        } finally {
            setUploading(false);
            // Reset file input
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    };

    if (loading || !profileUser) {
        return <div className="profile-container">Loading...</div>;
    }

    const avatarUrl = getAvatarUrl();
    const displayName = profileUser.display_name || profileUser.full_name || profileUser.username || "User";

    return (
        <div className="profile-container">
            <div className="profile-card">
                <div className="profile-header">
                    <div className="profile-avatar-section">
                        <div className="profile-avatar-wrapper">
                            {avatarUrl ? (
                                <img 
                                    src={avatarUrl} 
                                    alt="Profile" 
                                    className="profile-avatar"
                                    onError={(e) => {
                                        // Fallback to a default avatar or hide image
                                        e.target.style.display = 'none';
                                    }}
                                />
                            ) : (
                                <div className="profile-avatar-placeholder">
                                    {displayName.charAt(0).toUpperCase()}
                                </div>
                            )}
                            {isOwnProfile && (
                                <div className="profile-avatar-overlay">
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept="image/*"
                                        onChange={handleAvatarChange}
                                        style={{ display: "none" }}
                                        id="avatar-upload"
                                        disabled={uploading}
                                    />
                                    <label 
                                        htmlFor="avatar-upload" 
                                        className="avatar-upload-button"
                                        title="Change profile picture"
                                    >
                                        {uploading ? "..." : "📷"}
                                    </label>
                                </div>
                            )}
                        </div>
                    </div>
                    <h1 className="profile-name">{displayName}</h1>
                    <div className="profile-details">
                        {profileUser.username && (
                            <div className="profile-detail-item">
                                <span className="profile-detail-label">Username:</span>
                                <span className="profile-detail-value">@{profileUser.username}</span>
                            </div>
                        )}
                        {isOwnProfile && (
                            <div className="profile-detail-item">
                                <span className="profile-detail-label">Email:</span>
                                <span className="profile-detail-value">{profileUser.email}</span>
                            </div>
                        )}
                    </div>
                    {error && (
                        <div className="profile-error">{error}</div>
                    )}
                    {isOwnProfile && (
                        <button 
                            onClick={logout} 
                            className="logout-btn profile-logout"
                        >
                            Logout
                        </button>
                    )}
                </div>
            </div>

            {/* Connection Insights - Only visible to profile owner */}
            {isOwnProfile && <ConnectionInsights />}

            {/* User's Posts */}
            <div className="profile-posts-section">
                <h2 className="profile-posts-title">
                    {isOwnProfile ? "My Posts" : `${displayName}'s Posts`} ({posts.length})
                </h2>
                {posts.length === 0 ? (
                    <div className="empty-state">
                        <p>{isOwnProfile ? "You haven't posted anything yet." : `${displayName} hasn't posted anything yet.`}</p>
                    </div>
                ) : (
                    <div className="feed-list">
                        {posts.map((post) => (
                            <article key={post.id} className="post-card">
                                <div className="post-meta">
                                    <span className="author-name">
                                        @{post.author.username}
                                    </span>
                                    <div className="post-meta-actions">
                                        <span className="post-date">
                                            {new Date(post.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                        </span>
                                        {isOwnProfile && (
                                            <button
                                                onClick={() => handleDeletePost(post.id)}
                                                disabled={deletingPostId === post.id}
                                                className="delete-post-button"
                                                title="Delete post"
                                                aria-label="Delete post"
                                            >
                                                {deletingPostId === post.id ? "Deleting..." : "🗑️"}
                                            </button>
                                        )}
                                    </div>
                                </div>
                                {post.content && (
                                    <div className="post-content">
                                        {post.content.split('\n').map((paragraph, idx) => (
                                            <p key={idx}>{paragraph}</p>
                                        ))}
                                    </div>
                                )}
                                {post.photo_urls_presigned && post.photo_urls_presigned.length > 0 && (
                                    <div className="post-photos">
                                        {post.photo_urls_presigned.map((url, index) => (
                                            <img
                                                key={index}
                                                src={url}
                                                alt={`Post photo ${index + 1}`}
                                                className="post-image"
                                                loading="lazy"
                                                onError={(e) => {
                                                    console.error(`Failed to load image ${index + 1} for post ${post.id}`);
                                                    e.target.style.display = 'none';
                                                }}
                                            />
                                        ))}
                                    </div>
                                )}
                                {post.audience_tags && post.audience_tags.length > 0 && (
                                    <div className="tags-container">
                                        {post.audience_tags.map((tag) => (
                                            <span key={tag.id} className={`tag tag-${tag.color_scheme || 'generic'}`}>
                                                {tag.name}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </article>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
