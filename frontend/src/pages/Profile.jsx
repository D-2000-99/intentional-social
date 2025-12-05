import { useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import imageCompression from "browser-image-compression";

export default function Profile() {
    const { user, token, logout, refreshUser } = useAuth();
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    // Get avatar URL - prefer avatar_url (user-uploaded) over picture_url (Google)
    // The backend should return presigned URLs for S3 avatars
    const getAvatarUrl = () => {
        if (user?.avatar_url) {
            return user.avatar_url;
        }
        return user?.picture_url || null;
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

    if (!user) {
        return <div className="profile-container">Loading...</div>;
    }

    const avatarUrl = getAvatarUrl();
    const displayName = user.display_name || user.full_name || user.username || "User";

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
                        </div>
                    </div>
                    <h1 className="profile-name">{displayName}</h1>
                    <div className="profile-details">
                        <div className="profile-detail-item">
                            <span className="profile-detail-label">User ID:</span>
                            <span className="profile-detail-value">{user.id}</span>
                        </div>
                        <div className="profile-detail-item">
                            <span className="profile-detail-label">Email:</span>
                            <span className="profile-detail-value">{user.email}</span>
                        </div>
                        {user.username && (
                            <div className="profile-detail-item">
                                <span className="profile-detail-label">Username:</span>
                                <span className="profile-detail-value">@{user.username}</span>
                            </div>
                        )}
                    </div>
                    {error && (
                        <div className="profile-error">{error}</div>
                    )}
                    <button 
                        onClick={logout} 
                        className="logout-btn profile-logout"
                    >
                        Logout
                    </button>
                </div>
            </div>
        </div>
    );
}
