import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
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

            <section className="create-post-card">
                <div className="create-header">What's on your mind?</div>
                <form onSubmit={handlePost}>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="Share a meaningful thought..."
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
                                        aria-label={`Remove photo ${index + 1}`}
                                    >
                                        ×
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    
                    <div className="create-actions">
                        <div className="action-left">
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
                                📷 Add Photo
                            </label>
                            <AudienceSelector onAudienceChange={setAudience} />
                        </div>
                        <button type="submit" className="btn-primary" disabled={uploading}>
                            {uploading ? "Posting..." : "Post"}
                        </button>
                    </div>
                </form>
            </section>

            <div className="feed-list">
                {loading ? (
                    <p className="loading-state">Loading...</p>
                ) : posts.length === 0 ? (
                    <div className="empty-state">
                        <p>Your feed is quiet.</p>
                        <p>Follow people to see their thoughts here.</p>
                    </div>
                ) : (
                    posts.map((post) => (
                        <article key={post.id} className="post-card">
                            <div className="post-meta">
                                <Link 
                                    to={`/profile/${post.author.username}`}
                                    className="author-name author-link"
                                >
                                    {post.author.display_name || post.author.full_name || post.author.username}
                                </Link>
                                <span className="post-date">
                                    {new Date(post.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                </span>
                            </div>
                            {post.content && (
                                <div className="post-content">
                                    {post.content.split('\n').map((paragraph, idx) => (
                                        <p key={idx}>{paragraph}</p>
                                    ))}
                                </div>
                            )}
                            {/* Display photos */}
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
                    ))
                )}
            </div>
        </div>
    );
}
