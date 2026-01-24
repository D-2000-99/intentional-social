import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PhotoGallery from "./PhotoGallery";
import { sanitizeText, sanitizeUrlParam, validateContent } from "../utils/security";
import { MoreVertical, ChevronDown, ChevronRight } from "lucide-react";

export default function PostCard({ post, currentUser, onPostDeleted, showDeleteButton = false, notificationSummary }) {
    const [commentsExpanded, setCommentsExpanded] = useState(false);
    const [comments, setComments] = useState([]);
    const [loadingComments, setLoadingComments] = useState(false);
    const [commentContent, setCommentContent] = useState("");
    const [submittingComment, setSubmittingComment] = useState(false);
    const [reporting, setReporting] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef(null);
    const commentsSectionRef = useRef(null);
    const { token } = useAuth();

    // Reply state
    const [expandedReplyCommentId, setExpandedReplyCommentId] = useState(null);
    const [repliesByCommentId, setRepliesByCommentId] = useState({});
    const [loadingReplies, setLoadingReplies] = useState({});
    const [replyContent, setReplyContent] = useState("");
    const [submittingReply, setSubmittingReply] = useState(false);
    
    // Track if this is an auto-expand (from bell click) vs manual expand
    const isAutoExpandingRef = useRef(false);
    
    // Local notification state (updated from prop and when clearing)
    const [localNotificationSummary, setLocalNotificationSummary] = useState(
        notificationSummary || { has_unread_comments: false, has_unread_replies: false }
    );

    // Update local notification summary when prop changes
    useEffect(() => {
        if (notificationSummary) {
            setLocalNotificationSummary(notificationSummary);
        }
    }, [notificationSummary]);

    // Listen for auto-expand events (when jumping to post via bell)
    useEffect(() => {
        const handleAutoExpand = async (event) => {
            if (event.detail.postId === post.id) {
                // Auto-expand comments if there are unread notifications
                if (localNotificationSummary.has_unread_comments || localNotificationSummary.has_unread_replies) {
                    if (!commentsExpanded) {
                        isAutoExpandingRef.current = true;
                        
                        // Fetch comments if needed
                        if (comments.length === 0) {
                            setLoadingComments(true);
                            try {
                                const data = await api.getPostComments(token, post.id);
                                setComments(data);
                                
                                // Auto-expand replies for comments with unread replies
                                setTimeout(() => {
                                    data.forEach(comment => {
                                        if (comment.has_unread_reply) {
                                            handleToggleReplies(comment.id);
                                        }
                                    });
                                }, 100);
                            } catch (err) {
                                console.error("Failed to fetch comments", err);
                            } finally {
                                setLoadingComments(false);
                            }
                        }
                        
                        setCommentsExpanded(true);
                        
                        // Reset flag after a delay
                        setTimeout(() => {
                            isAutoExpandingRef.current = false;
                        }, 500);
                    }
                }
            }
        };
        
        window.addEventListener('auto-expand-comments', handleAutoExpand);
        
        return () => {
            window.removeEventListener('auto-expand-comments', handleAutoExpand);
        };
    }, [post.id, localNotificationSummary, commentsExpanded, comments.length, token]);

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

    const markPostNotificationsRead = async () => {
        if (!token || !localNotificationSummary.has_unread_comments && !localNotificationSummary.has_unread_replies) {
            return;
        }
        
        try {
            await api.markPostNotificationsRead(token, post.id);
            setLocalNotificationSummary({ has_unread_comments: false, has_unread_replies: false });
            // Trigger refresh event for bell
            window.dispatchEvent(new CustomEvent('notification-refresh'));
        } catch (err) {
            console.error("Failed to mark post notifications as read", err);
        }
    };

    const markCommentNotificationsRead = async (commentId) => {
        if (!token) return;
        
        try {
            await api.markCommentNotificationsRead(token, commentId);
            // Update comment in local state
            setComments(prev => prev.map(c => 
                c.id === commentId ? { ...c, has_unread_reply: false } : c
            ));
            // Trigger refresh event for bell
            window.dispatchEvent(new CustomEvent('notification-refresh'));
        } catch (err) {
            console.error("Failed to mark comment notifications as read", err);
        }
    };

    const handleToggleComments = async () => {
        const willExpand = !commentsExpanded;
        const isAutoExpand = isAutoExpandingRef.current;
        
        if (willExpand && comments.length === 0) {
            // Fetch comments when expanding for the first time
            setLoadingComments(true);
            try {
                const data = await api.getPostComments(token, post.id);
                setComments(data);
                
                // After loading comments, auto-expand replies for comments with unread replies
                // Only do this on auto-expand (from bell click), not manual expand
                if (isAutoExpand) {
                    setTimeout(() => {
                        data.forEach(comment => {
                            if (comment.has_unread_reply) {
                                handleToggleReplies(comment.id);
                            }
                        });
                    }, 100);
                }
            } catch (err) {
                console.error("Failed to fetch comments", err);
                if (!isAutoExpand) {
                    alert(`Failed to load comments: ${err.message}`);
                }
            } finally {
                setLoadingComments(false);
            }
        }
        
        setCommentsExpanded(willExpand);
        
        // Clear notifications when manually opening comments (not on auto-expand)
        if (willExpand && !isAutoExpand) {
            markPostNotificationsRead();
        }
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

    const handleToggleReplies = async (commentId) => {
        if (expandedReplyCommentId === commentId) {
            // Collapse replies
            setExpandedReplyCommentId(null);
            setReplyContent("");
        } else {
            // Expand and fetch replies if not already loaded
            setExpandedReplyCommentId(commentId);
            setReplyContent("");

            if (!repliesByCommentId[commentId]) {
                setLoadingReplies(prev => ({ ...prev, [commentId]: true }));
                try {
                    const data = await api.getCommentReplies(token, commentId);
                    setRepliesByCommentId(prev => ({ ...prev, [commentId]: data }));
                } catch (err) {
                    console.error("Failed to fetch replies", err);
                } finally {
                    setLoadingReplies(prev => ({ ...prev, [commentId]: false }));
                }
            }
            
            // Clear comment notifications when opening replies
            const comment = comments.find(c => c.id === commentId);
            if (comment && comment.has_unread_reply) {
                markCommentNotificationsRead(commentId);
            }
        }
    };

    const handleSubmitReply = async (e, commentId) => {
        e.preventDefault();
        if (!replyContent.trim()) return;

        const validation = validateContent(replyContent, 2000);
        if (!validation.isValid) {
            alert(validation.error || 'Invalid reply content');
            return;
        }

        setSubmittingReply(true);
        try {
            const newReply = await api.createReply(token, commentId, validation.sanitized);
            setRepliesByCommentId(prev => ({
                ...prev,
                [commentId]: [...(prev[commentId] || []), newReply]
            }));
            setReplyContent("");
        } catch (err) {
            console.error("Failed to create reply", err);
            alert(`Failed to post reply: ${err.message}`);
        } finally {
            setSubmittingReply(false);
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
                                <MoreVertical size={20} />
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
            <div className="comments-section" ref={commentsSectionRef}>
                <div
                    className="comments-toggle-button"
                    onClick={handleToggleComments}
                    aria-expanded={commentsExpanded}
                >
                    {commentsExpanded ? "▼" : "▶"} Comments {comments.length > 0 && `(${comments.length})`}
                    {(localNotificationSummary.has_unread_comments || localNotificationSummary.has_unread_replies) && (
                        <span className="notification-dot"></span>
                    )}
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
                                                <div
                                                    className="comment-main"
                                                    onClick={() => handleToggleReplies(comment.id)}
                                                    style={{ cursor: 'pointer' }}
                                                >
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
                                                    <div className="comment-reply-hint">
                                                        {expandedReplyCommentId === comment.id ? <ChevronDown size={12} /> : <ChevronRight size={12} />} Reply
                                                        {repliesByCommentId[comment.id]?.length > 0 &&
                                                            ` (${repliesByCommentId[comment.id].length})`}
                                                        {comment.has_unread_reply && (
                                                            <span className="notification-dot"></span>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Replies section - shown when comment is tapped */}
                                                {expandedReplyCommentId === comment.id && (
                                                    <div className="replies-section">
                                                        {loadingReplies[comment.id] ? (
                                                            <div className="replies-loading">Loading replies...</div>
                                                        ) : (
                                                            <>
                                                                {/* Replies list */}
                                                                {repliesByCommentId[comment.id]?.length > 0 && (
                                                                    <div className="replies-list">
                                                                        {repliesByCommentId[comment.id].map((reply) => (
                                                                            <div key={reply.id} className="reply-item">
                                                                                <div className="reply-header">
                                                                                    <span className="reply-author">
                                                                                        @{sanitizeText(reply.author?.username || '')}
                                                                                    </span>
                                                                                    <span className="reply-date">
                                                                                        {new Date(reply.created_at).toLocaleDateString('en-US', {
                                                                                            month: 'short',
                                                                                            day: 'numeric',
                                                                                            hour: 'numeric',
                                                                                            minute: '2-digit'
                                                                                        })}
                                                                                    </span>
                                                                                </div>
                                                                                <div className="reply-content">
                                                                                    {sanitizeText(reply.content || '')}
                                                                                </div>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                )}

                                                                {/* Reply form */}
                                                                <form
                                                                    onSubmit={(e) => handleSubmitReply(e, comment.id)}
                                                                    className="reply-form"
                                                                    onClick={(e) => e.stopPropagation()}
                                                                >
                                                                    <textarea
                                                                        value={replyContent}
                                                                        onChange={(e) => setReplyContent(e.target.value)}
                                                                        placeholder="Write a reply..."
                                                                        rows="2"
                                                                        className="reply-input"
                                                                        onClick={(e) => e.stopPropagation()}
                                                                    />
                                                                    <button
                                                                        type="submit"
                                                                        className="reply-submit-button"
                                                                        disabled={submittingReply || !replyContent.trim()}
                                                                    >
                                                                        {submittingReply ? "Posting..." : "Reply"}
                                                                    </button>
                                                                </form>
                                                            </>
                                                        )}
                                                    </div>
                                                )}
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
