import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PhotoGallery from "./PhotoGallery";
import { sanitizeText, sanitizeUrlParam, validateContent } from "../utils/security";

export default function PostCard({ post, currentUser, onPostDeleted, showDeleteButton = false }) {
    const [commentsExpanded, setCommentsExpanded] = useState(false);
    const [comments, setComments] = useState([]);
    const [loadingComments, setLoadingComments] = useState(false);
    const [commentContent, setCommentContent] = useState("");
    const [submittingComment, setSubmittingComment] = useState(false);
    const [reporting, setReporting] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef(null);
    const { token } = useAuth();

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setMenuOpen(false);
            }
        };

        if (menuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [menuOpen]);

    const handleToggleComments = async () => {
        if (!commentsExpanded && comments.length === 0) {
            // Fetch comments when expanding for the first time
            setLoadingComments(true);
            try {
                const data = await api.getPostComments(token, post.id);
                setComments(data);
            } catch (err) {
                console.error("Failed to fetch comments", err);
                alert(`Failed to load comments: ${err.message}`);
            } finally {
                setLoadingComments(false);
            }
        }
        setCommentsExpanded(!commentsExpanded);
    };

    const handleSubmitComment = async (e) => {
        e.preventDefault();
        if (!commentContent.trim()) return;

        // Validate and sanitize comment content
        const validation = validateContent(commentContent, 5000); // Max 5000 chars for comments
        if (!validation.isValid) {
            alert(validation.error || 'Invalid comment content');
            return;
        }

        setSubmittingComment(true);
        try {
            const newComment = await api.createComment(token, post.id, validation.sanitized);
            setComments([...comments, newComment]);
            setCommentContent("");
        } catch (err) {
            console.error("Failed to create comment", err);
            alert(`Failed to post comment: ${err.message}`);
        } finally {
            setSubmittingComment(false);
        }
    };

    const handleReportPost = async (postId) => {
        if (!confirm("Are you sure you want to report this post?")) {
            return;
        }
        
        setReporting(true);
        try {
            await api.reportPost(token, postId);
            alert("Post reported successfully. Thank you for your feedback.");
        } catch (err) {
            console.error("Failed to report post", err);
            alert(`Failed to report post: ${err.message}`);
        } finally {
            setReporting(false);
        }
    };

    return (
        <article className="post-card">
            <div className="post-meta">
                {post.author ? (
                    <Link 
                        to={`/profile/${sanitizeUrlParam(post.author.username || '')}`}
                        className="author-name author-link"
                    >
                        @{sanitizeText(post.author.username || '')}
                    </Link>
                ) : (
                    <span className="author-name">
                        {sanitizeText(post.author?.display_name || post.author?.full_name || post.author?.username || "Unknown")}
                    </span>
                )}
                <div className="post-meta-actions">
                    <span className="post-date">
                        {new Date(post.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    {/* 3 dots menu - show if there are actions available */}
                    {(post.author_id !== currentUser?.id || (showDeleteButton && onPostDeleted)) && (
                        <div className="kebab-menu-container" ref={menuRef}>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setMenuOpen(!menuOpen);
                                }}
                                className="kebab-menu-button"
                                title="More options"
                                aria-label="More options"
                            >
                                ⋮
                            </button>
                            {menuOpen && (
                                <div className="kebab-menu-popover">
                                    {post.author_id !== currentUser?.id && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setMenuOpen(false);
                                                handleReportPost(post.id);
                                            }}
                                            className="kebab-menu-item kebab-menu-item-danger"
                                            disabled={reporting}
                                        >
                                            {reporting ? "Reporting..." : "Report post"}
                                        </button>
                                    )}
                                    {showDeleteButton && onPostDeleted && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setMenuOpen(false);
                                                onPostDeleted(post.id);
                                            }}
                                            className="kebab-menu-item kebab-menu-item-danger"
                                        >
                                            Delete post
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
            
            {post.content && (
                <div className="post-content">
                    {sanitizeText(post.content).split('\n').map((paragraph, idx) => (
                        <p key={idx}>{paragraph}</p>
                    ))}
                </div>
            )}
            
            {/* Display photos */}
            {post.photo_urls_presigned && post.photo_urls_presigned.length > 0 && (
                <div className="post-photos" onClick={(e) => e.stopPropagation()}>
                    <PhotoGallery photos={post.photo_urls_presigned} />
                </div>
            )}
            
            {/* Only show tags if this is the current user's own post */}
            {post.author_id === currentUser?.id && post.audience_tags && post.audience_tags.length > 0 && (
                <div className="tags-container">
                                    {post.audience_tags.map((tag) => (
                                        <span key={tag.id} className={`tag tag-${sanitizeUrlParam(tag.color_scheme || 'generic')}`}>
                                            {sanitizeText(tag.name || '')}
                                        </span>
                                    ))}
                </div>
            )}

            {/* Comments section */}
            <div className="comments-section">
                <div 
                    className="comments-toggle-button"
                    onClick={handleToggleComments}
                    aria-expanded={commentsExpanded}
                >
                    {commentsExpanded ? "▼" : "▶"} Comments {comments.length > 0 && `(${comments.length})`}
                </div>

                {commentsExpanded && (
                    <div className="comments-container">
                        {loadingComments ? (
                            <div className="comments-loading">Loading comments...</div>
                        ) : (
                            <>
                                {/* Comments list */}
                                <div className="comments-list">
                                    {comments.length === 0 ? (
                                        <div className="no-comments">No comments yet. Be the first to comment!</div>
                                    ) : (
                                        comments.map((comment) => (
                                            <div key={comment.id} className="comment-item">
                                                <div className="comment-header">
                                                    <span className="comment-author">
                                                        @{sanitizeText(comment.author?.username || '')}
                                                    </span>
                                                    <span className="comment-date">
                                                        {new Date(comment.created_at).toLocaleDateString('en-US', { 
                                                            month: 'short', 
                                                            day: 'numeric',
                                                            hour: 'numeric',
                                                            minute: '2-digit'
                                                        })}
                                                    </span>
                                                </div>
                                                <div className="comment-content">
                                                    {sanitizeText(comment.content || '')}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>

                                {/* Comment form */}
                                <form onSubmit={handleSubmitComment} className="comment-form">
                                    <textarea
                                        value={commentContent}
                                        onChange={(e) => setCommentContent(e.target.value)}
                                        placeholder="Write a comment..."
                                        rows="2"
                                        className="comment-input"
                                    />
                                    <button 
                                        type="submit" 
                                        className="comment-submit-button"
                                        disabled={submittingComment || !commentContent.trim()}
                                    >
                                        {submittingComment ? "Posting..." : "Post Comment"}
                                    </button>
                                </form>
                            </>
                        )}
                    </div>
                )}
            </div>
        </article>
    );
}
