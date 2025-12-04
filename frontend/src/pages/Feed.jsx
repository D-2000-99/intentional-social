import { useState, useEffect, useRef } from "react";
import imageCompression from "browser-image-compression";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import FeedFilterBar from "../components/FeedFilterBar";
import AudienceSelector from "../components/AudienceSelector";

export default function Feed() {
    const [posts, setPosts] = useState([]);
    const [content, setContent] = useState("");
    const [loading, setLoading] = useState(true);
    const [selectedTagIds, setSelectedTagIds] = useState([]);
    const [audience, setAudience] = useState({ audience_type: 'all', audience_tag_ids: [] });
    const [selectedPhotos, setSelectedPhotos] = useState([]);
    const [photoPreviews, setPhotoPreviews] = useState([]);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);
    const { token } = useAuth();

    const fetchFeed = async (tagIds = []) => {
        try {
            let data;
            if (tagIds.length > 0) {
                const tagIdsParam = tagIds.join(',');
                data = await api.request(`/feed?tag_ids=${tagIdsParam}`, "GET", null, token);
            } else {
                data = await api.getFeed(token);
            }
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
            console.error("Failed to fetch feed", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFeed(selectedTagIds);
    }, [token, selectedTagIds]);

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

    const handlePhotoSelect = async (e) => {
        const files = Array.from(e.target.files || []);
        if (files.length === 0) return;

        // Limit to 5 photos total
        const maxPhotos = 5;
        const remainingSlots = maxPhotos - selectedPhotos.length;
        if (files.length > remainingSlots) {
            alert(`You can only add up to ${maxPhotos} photos. Please select ${remainingSlots} or fewer.`);
            files.splice(remainingSlots);
        }

        try {
            const compressedFiles = await Promise.all(
                files.map(file => compressImage(file))
            );

            // Create preview URLs
            const newPreviews = compressedFiles.map(file => URL.createObjectURL(file));
            
            setSelectedPhotos(prev => [...prev, ...compressedFiles]);
            setPhotoPreviews(prev => [...prev, ...newPreviews]);
        } catch (error) {
            alert(`Failed to process images: ${error.message}`);
        }

        // Reset file input
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const removePhoto = (index) => {
        // Revoke preview URL to free memory
        if (photoPreviews[index]) {
            URL.revokeObjectURL(photoPreviews[index]);
        }
        
        setSelectedPhotos(prev => prev.filter((_, i) => i !== index));
        setPhotoPreviews(prev => prev.filter((_, i) => i !== index));
    };

    const handlePost = async (e) => {
        e.preventDefault();
        if (!content.trim() && selectedPhotos.length === 0) return;

        setUploading(true);
        try {
            await api.createPost(
                token,
                content,
                audience.audience_type,
                audience.audience_tag_ids,
                selectedPhotos
            );
            
            // Clear form
            setContent("");
            setAudience({ audience_type: 'all', audience_tag_ids: [] });
            
            // Clear photos and revoke preview URLs
            photoPreviews.forEach(url => URL.revokeObjectURL(url));
            setSelectedPhotos([]);
            setPhotoPreviews([]);
            
            // Reset file input
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
            
            fetchFeed(selectedTagIds); // Refresh feed
        } catch (err) {
            alert(`Failed to post: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="feed-container">
            <FeedFilterBar onFilterChange={setSelectedTagIds} />

            <div className="create-post">
                <form onSubmit={handlePost}>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="What's on your mind?"
                        rows="3"
                    />
                    
                    {/* Photo previews */}
                    {photoPreviews.length > 0 && (
                        <div className="photo-previews">
                            {photoPreviews.map((preview, index) => (
                                <div key={index} className="photo-preview">
                                    <img src={preview} alt={`Preview ${index + 1}`} />
                                    <button
                                        type="button"
                                        onClick={() => removePhoto(index)}
                                        className="remove-photo"
                                    >
                                        ×
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    
                    <div className="post-actions">
                        <div className="post-actions-left">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                multiple
                                onChange={handlePhotoSelect}
                                style={{ display: "none" }}
                                id="photo-upload"
                            />
                            <label htmlFor="photo-upload" className="photo-upload-button">
                                📷 Add Photos
                            </label>
                            <AudienceSelector onAudienceChange={setAudience} />
                        </div>
                        <button type="submit" disabled={uploading}>
                            {uploading ? "Posting..." : "Post"}
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
                    ))
                )}
            </div>
        </div>
    );
}
