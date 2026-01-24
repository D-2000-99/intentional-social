import { useState, useEffect, useRef, useCallback } from "react";
import imageCompression from "browser-image-compression";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import FeedFilterBar from "../components/FeedFilterBar";
import AudienceSelector from "../components/AudienceSelector";
import PostCard from "../components/PostCard";
import DigestView from "../components/DigestView";
import { validateContent } from "../utils/security";
import { Camera, X } from "lucide-react";

export default function Feed() {
    const [mode, setMode] = useState("now"); // "now" or "digest"

    // Notify Layout (navbar) when feed mode changes so bell is shown only in "Now"
    useEffect(() => {
        window.dispatchEvent(new CustomEvent("feed-mode-change", { detail: { mode } }));
    }, [mode]);

    const [posts, setPosts] = useState([]);
    const [content, setContent] = useState("");
    const [loading, setLoading] = useState(true);
    const [selectedTagIds, setSelectedTagIds] = useState([]);
    const [audience, setAudience] = useState({ audience_type: 'all', audience_tag_ids: [] });
    const [selectedPhotos, setSelectedPhotos] = useState([]);
    const [photoPreviews, setPhotoPreviews] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [notificationSummary, setNotificationSummary] = useState({});
    const fileInputRef = useRef(null);
    const { token, user: currentUser } = useAuth();

    const fetchFeed = useCallback(async (tagIds = [], skip = 0) => {
        setLoading(true);
        try {
            let data;
            if (tagIds.length > 0) {
                const tagIdsParam = tagIds.join(',');
                data = await api.request(`/feed?tag_ids=${tagIdsParam}&skip=${skip}&limit=20`, "GET", null, token);
            } else {
                data = await api.getFeed(token, skip, 20);
            }
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
            if (skip === 0) {
                setPosts(data);
            } else {
                setPosts(prev => [...prev, ...data]);
            }
        } catch (err) {
            console.error("Failed to fetch feed", err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    const loadMore = useCallback(async () => {
        if (loading) return;
        await fetchFeed(selectedTagIds, posts.length);
    }, [fetchFeed, selectedTagIds, posts.length, loading]);

    const jumpToPost = useCallback(async (postId, onComplete) => {
        // Lock navbar
        window.dispatchEvent(new CustomEvent('lock-navbar'));
        
        // Mark scroll as programmatic
        window.dispatchEvent(new CustomEvent('programmatic-scroll'));
        
        // Helper function to scroll to post
        const scrollToPost = () => {
            const element = document.getElementById(`post-${postId}`);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
            }
            if (onComplete) onComplete();
        };
        
        // Check if post is already loaded
        const existingPost = posts.find(p => p.id === postId);
        if (existingPost) {
            // Post is already loaded, scroll to it
            setTimeout(scrollToPost, 100);
            return;
        }
        
        // Post not loaded, need to fetch more
        // Load up to 50 posts total
        const maxPosts = 50;
        let currentSkip = posts.length;
        let found = false;
        
        while (currentSkip < maxPosts && !found) {
            try {
                let data;
                if (selectedTagIds.length > 0) {
                    const tagIdsParam = selectedTagIds.join(',');
                    data = await api.request(`/feed?tag_ids=${tagIdsParam}&skip=${currentSkip}&limit=20`, "GET", null, token);
                } else {
                    data = await api.getFeed(token, currentSkip, 20);
                }
                
                if (data.length === 0) break; // No more posts
                
                // Add new posts
                setPosts(prev => {
                    const newPosts = [...prev, ...data];
                    return newPosts;
                });
                
                // Check if target post is in this batch
                const targetPost = data.find(p => p.id === postId);
                if (targetPost) {
                    found = true;
                    // Wait for DOM update, then scroll
                    setTimeout(() => {
                        scrollToPost();
                    }, 300);
                    break;
                }
                
                currentSkip += data.length;
            } catch (err) {
                console.error("Failed to load more posts", err);
                if (onComplete) onComplete();
                break;
            }
        }
        
        if (!found) {
            console.warn(`Post ${postId} not found in recent 50 posts`);
            if (onComplete) onComplete();
        }
    }, [posts, selectedTagIds, token]);

    useEffect(() => {
        fetchFeed(selectedTagIds);
    }, [fetchFeed, selectedTagIds]);

    // Fetch notification summary when posts change
    useEffect(() => {
        const fetchNotificationSummary = async () => {
            if (!token || posts.length === 0) return;
            
            try {
                const postIds = posts.map(p => p.id);
                const summary = await api.getPostNotificationSummary(token, postIds);
                setNotificationSummary(summary.summary || {});
            } catch (err) {
                console.error("Failed to fetch notification summary", err);
            }
        };
        
        fetchNotificationSummary();
    }, [posts, token]);

    // Listen for jump-to-post events
    useEffect(() => {
        const handleJumpToPost = (event) => {
            const { postId, onComplete } = event.detail;
            jumpToPost(postId, onComplete);
        };
        
        window.addEventListener('jump-to-post', handleJumpToPost);
        
        return () => {
            window.removeEventListener('jump-to-post', handleJumpToPost);
        };
    }, [jumpToPost]);

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

        // Limit to 3 photos total per post
        const maxPhotos = 3;
        const remainingSlots = maxPhotos - selectedPhotos.length;
        if (remainingSlots <= 0) {
            alert(`You can only add up to ${maxPhotos} photos per post. Please remove a photo first.`);
            return;
        }
        if (files.length > remainingSlots) {
            alert(`You can only add ${remainingSlots} more photo${remainingSlots === 1 ? '' : 's'}. Only the first ${remainingSlots} will be added.`);
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

        // Validate and sanitize post content if provided
        let sanitizedContent = '';
        if (content.trim()) {
            const validation = validateContent(content, 10000); // Max 10000 chars for posts
            if (!validation.isValid) {
                alert(validation.error || 'Invalid post content');
                return;
            }
            sanitizedContent = validation.sanitized;
        }

        setUploading(true);
        try {
            await api.createPost(
                token,
                sanitizedContent,
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
            {/* Mode Toggle */}
            <div className="mode-toggle">
                <button
                    className={`mode-toggle-button ${mode === "now" ? "active" : ""}`}
                    onClick={() => setMode("now")}
                >
                    Now
                </button>
                <button
                    className={`mode-toggle-button ${mode === "digest" ? "active" : ""}`}
                    onClick={() => setMode("digest")}
                >
                    Digest
                </button>
            </div>

            {mode === "digest" ? (
                <DigestView onSwitchToNow={() => setMode("now")} />
            ) : (
                <>
                    <FeedFilterBar onFilterChange={setSelectedTagIds} />

                    <section className="create-post-card">
                        <div className="create-header">What's on your mind?</div>
                        <form onSubmit={handlePost}>
                            <textarea
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                placeholder="Share a meaningful thought..."
                                rows="4"
                                style={{ minHeight: '120px' }}
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
                                                <X size={16} />
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
                                    <label
                                        htmlFor="photo-upload"
                                        className={`photo-upload-button ${selectedPhotos.length >= 3 ? 'disabled' : ''}`}
                                        onClick={(e) => selectedPhotos.length >= 3 && e.preventDefault()}
                                    >
                                        <Camera size={16} />
                                        Add Photo
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
                                <div key={post.id} id={`post-${post.id}`}>
                                    <PostCard
                                        post={post}
                                        currentUser={currentUser}
                                        notificationSummary={notificationSummary[post.id]}
                                    />
                                </div>
                            ))
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
