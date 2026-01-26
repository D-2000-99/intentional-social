import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PhotoGallery from "./PhotoGallery";
import { sanitizeText, sanitizeUrlParam, validateContent } from "../utils/security";
import { extractUrls, isMusicPlatformUrl, fetchLinkPreview } from "../utils/linkPreview";
import { linkifyText } from "../utils/textUtils";
import { MoreVertical, ChevronDown, ChevronRight, MessageCircle, Smile } from "lucide-react";

// Configuration: Long press duration in milliseconds to show reactions modal
const LONG_PRESS_DURATION_MS = 350;

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
    
    // Reaction state
    const [reactions, setReactions] = useState([]); // Array of individual reactions
    const [loadingReactions, setLoadingReactions] = useState(false);
    const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
    const [showingReactors, setShowingReactors] = useState(null); // Array of {user: {}, emoji: string}
    const [loadingReactors, setLoadingReactors] = useState(false);
    const emojiPickerRef = useRef(null);
    const longPressTimerRef = useRef(null);
    
    // Comment count state - initialize from post prop if available, otherwise 0
    const [commentCount, setCommentCount] = useState(post.comment_count || 0);
    
    // Link preview state - support multiple previews
    const [linkPreviews, setLinkPreviews] = useState([]);
    const [loadingLinkPreview, setLoadingLinkPreview] = useState(false);
    const [failedMusicUrls, setFailedMusicUrls] = useState([]); // Track failed music URLs to show them
    
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

    // Close emoji picker when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (emojiPickerRef.current && !emojiPickerRef.current.contains(event.target)) {
                setEmojiPickerOpen(false);
            }
        };

        if (emojiPickerOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [emojiPickerOpen]);

    // Fetch reactions when component mounts
    useEffect(() => {
        const fetchReactions = async () => {
            if (!token) return;
            setLoadingReactions(true);
            try {
                const data = await api.getPostReactions(token, post.id);
                setReactions(data || []);
            } catch (err) {
                console.error("Failed to fetch reactions", err);
            } finally {
                setLoadingReactions(false);
            }
        };
        fetchReactions();
    }, [post.id, token]);

    // Update comment count when post prop changes (e.g., when feed refreshes)
    useEffect(() => {
        if (post.comment_count !== undefined) {
            setCommentCount(post.comment_count);
        }
    }, [post.comment_count]);
    
    // Only fetch comment count if not provided in post prop (fallback for other views)
    useEffect(() => {
        if (post.comment_count === undefined) {
            const fetchCommentCount = async () => {
                if (!token) return;
                try {
                    const data = await api.getPostCommentCount(token, post.id);
                    setCommentCount(data.count || 0);
                } catch (err) {
                    console.error("Failed to fetch comment count", err);
                    // Don't show error to user, just leave count at 0
                }
            };
            fetchCommentCount();
        }
    }, [post.id, post.comment_count, token]);

    // Fetch link previews when component mounts
    useEffect(() => {
        const fetchPreviews = async () => {
            if (!post.content) return;
            
            const urls = extractUrls(post.content);
            if (urls.length === 0) return;
            
            setLoadingLinkPreview(true);
            setFailedMusicUrls([]); // Reset failed URLs
            try {
                const previews = [];
                const failedUrls = [];
                const maxPreviews = 3;
                
                // Separate music platform URLs and other URLs
                const musicUrls = urls.filter(url => isMusicPlatformUrl(url));
                const otherUrls = urls.filter(url => !isMusicPlatformUrl(url));
                
                // Prioritize music platform URLs, then other URLs
                const urlsToFetch = [...musicUrls, ...otherUrls].slice(0, maxPreviews);
                
                // Fetch previews for all URLs (up to max)
                for (const url of urlsToFetch) {
                    try {
                        const preview = await fetchLinkPreview(url);
                        if (preview) {
                            previews.push(preview);
                            // Stop if we've reached the max
                            if (previews.length >= maxPreviews) {
                                break;
                            }
                        } else {
                            // If preview is null and it's a music URL, track it as failed
                            if (isMusicPlatformUrl(url)) {
                                failedUrls.push(url);
                            }
                        }
                    } catch (err) {
                        console.warn(`Failed to fetch preview for ${url}:`, err);
                        // If it's a music URL and failed, track it to show the URL
                        if (isMusicPlatformUrl(url)) {
                            failedUrls.push(url);
                        }
                        // Continue with next URL even if one fails
                    }
                }
                
                setLinkPreviews(previews);
                setFailedMusicUrls(failedUrls);
            } catch (err) {
                console.warn("Failed to fetch link previews:", err);
            } finally {
                setLoadingLinkPreview(false);
            }
        };
        
        fetchPreviews();
    }, [post.content]);

    // Cleanup long press timer on unmount
    useEffect(() => {
        return () => {
            if (longPressTimerRef.current) {
                clearTimeout(longPressTimerRef.current);
            }
        };
    }, []);

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
        
        if (willExpand && comments.length === 0) {
            // Fetch comments when expanding for the first time
            setLoadingComments(true);
            try {
                const data = await api.getPostComments(token, post.id);
                setComments(data);
                // Update comment count to match loaded comments
                setCommentCount(data.length);
            } catch (err) {
                console.error("Failed to fetch comments", err);
                alert(`Failed to load comments: ${err.message}`);
            } finally {
                setLoadingComments(false);
            }
        }
        
        setCommentsExpanded(willExpand);
        
        // Clear notifications when manually opening comments
        if (willExpand) {
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
            setCommentCount(prev => prev + 1); // Update comment count
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

    // Reaction handlers
    const handleEmojiClick = async (emoji) => {
        if (!token) return;
        
        try {
            // Check if user already has a reaction
            const existingReaction = reactions.find(r => r.user_id === currentUser?.id);
            
            if (existingReaction) {
                // If clicking on their own reaction, remove it
                if (existingReaction.emoji === emoji) {
                    await api.removeReaction(token, post.id);
                } else {
                    // Update to new emoji
                    await api.createOrUpdateReaction(token, post.id, emoji);
                }
            } else {
                // Create new reaction
                await api.createOrUpdateReaction(token, post.id, emoji);
            }
            
            // Refresh reactions
            const data = await api.getPostReactions(token, post.id);
            setReactions(data || []);
            setEmojiPickerOpen(false);
        } catch (err) {
            console.error("Failed to handle reaction", err);
            alert(`Failed to react: ${err.message}`);
        }
    };

    const handleReactionClick = async (reaction) => {
        if (!token) return;
        
        // If clicking on own reaction, remove it
        if (reaction.user_id === currentUser?.id) {
            try {
                await api.removeReaction(token, post.id);
                // Refresh reactions
                const data = await api.getPostReactions(token, post.id);
                setReactions(data || []);
            } catch (err) {
                console.error("Failed to remove reaction", err);
                alert(`Failed to remove reaction: ${err.message}`);
            }
        }
    };

    const handleReactIconLongPress = async () => {
        if (!token) return;
        
        setLoadingReactors(true);
        try {
            const data = await api.getAllReactors(token, post.id);
            setShowingReactors(data || []);
        } catch (err) {
            console.error("Failed to fetch reactors", err);
        } finally {
            setLoadingReactors(false);
        }
    };

    const handleReactIconMouseDown = (e) => {
        e.preventDefault(); // Prevent text selection
        // Start long press timer - modal will open after LONG_PRESS_DURATION_MS while still holding
        longPressTimerRef.current = setTimeout(() => {
            handleReactIconLongPress();
            longPressTimerRef.current = null; // Clear ref after firing
        }, LONG_PRESS_DURATION_MS);
    };

    const handleReactIconMouseUp = (e) => {
        // Only cancel timer if it hasn't fired yet (user released before LONG_PRESS_DURATION_MS)
        // If timer already fired, modal is open, so don't prevent click
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current);
            longPressTimerRef.current = null;
        }
        // If modal is showing, prevent the click from opening emoji picker
        if (showingReactors) {
            e.preventDefault();
            e.stopPropagation();
        }
    };

    const handleReactIconMouseLeave = () => {
        // Cancel long press if mouse leaves before timeout
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current);
            longPressTimerRef.current = null;
        }
    };

    const handleReactIconTouchStart = (e) => {
        e.preventDefault(); // Prevent text selection and default touch behavior
        // Start long press timer - modal will open after LONG_PRESS_DURATION_MS while still holding
        longPressTimerRef.current = setTimeout(() => {
            handleReactIconLongPress();
            longPressTimerRef.current = null; // Clear ref after firing
        }, LONG_PRESS_DURATION_MS);
    };

    const handleReactIconTouchEnd = (e) => {
        // Only cancel timer if it hasn't fired yet (user released before LONG_PRESS_DURATION_MS)
        // If timer already fired, modal is open
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current);
            longPressTimerRef.current = null;
        }
        // If modal is showing, prevent the touch end from triggering click
        if (showingReactors) {
            e.preventDefault();
            e.stopPropagation();
        }
    };

    const handleReactIconTouchCancel = (e) => {
        // Cancel long press if touch is cancelled
        if (longPressTimerRef.current) {
            clearTimeout(longPressTimerRef.current);
            longPressTimerRef.current = null;
        }
    };

    // Group reactions by emoji for display
    const groupedReactions = reactions.reduce((acc, reaction) => {
        const emoji = reaction.emoji;
        if (!acc[emoji]) {
            acc[emoji] = {
                emoji,
                count: 0,
                userReacted: false,
                reactions: []
            };
        }
        acc[emoji].count++;
        acc[emoji].reactions.push(reaction);
        if (reaction.user_id === currentUser?.id) {
            acc[emoji].userReacted = true;
        }
        return acc;
    }, {});

    // Popular emojis for quick selection
    const popularEmojis = ['👍', '❤️', '😊', '😂', '😮', '😢', '🙏', '🔥'];

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

            {post.content && (() => {
                const content = sanitizeText(post.content);
                const urls = extractUrls(content);
                
                // Only hide music platform URLs that successfully fetched previews
                // Keep failed music URLs visible
                const musicUrls = urls.filter(url => isMusicPlatformUrl(url));
                const successfulMusicUrls = linkPreviews
                    .filter(preview => preview.url && isMusicPlatformUrl(preview.url))
                    .map(preview => preview.url);
                
                // Remove only successful music URLs, keep failed ones
                const musicUrlsToHide = musicUrls.filter(url => successfulMusicUrls.includes(url));
                const contentWithoutMusicUrls = musicUrlsToHide.reduce((text, url) => {
                    // Remove successful music platform URL from text
                    return text.replace(url, '').trim();
                }, content);
                
                // Check if content is only successful music URLs (after removing them, only whitespace remains)
                // But account for failed music URLs and other content
                const remainingContent = contentWithoutMusicUrls.trim();
                const hasFailedMusicUrls = failedMusicUrls.length > 0;
                const isOnlySuccessfulMusicUrls = musicUrlsToHide.length > 0 && 
                    remainingContent.length === 0 && 
                    !hasFailedMusicUrls &&
                    urls.filter(url => !isMusicPlatformUrl(url)).length === 0;
                
                // If only successful music URLs, don't show content. Otherwise show content.
                if (isOnlySuccessfulMusicUrls) {
                    return null; // Hide content if it's only successful music URLs
                }
                
                // Show content with only successful music URLs removed
                // Failed music URLs and other URLs will be visible and clickable
                return (
                    <div className="post-content">
                        {contentWithoutMusicUrls.split('\n').filter(p => p.trim()).map((paragraph, idx) => {
                            const linkified = linkifyText(paragraph);
                            return (
                                <p key={idx}>
                                    {linkified.map((part, partIdx) => {
                                        if (typeof part === 'string') {
                                            return <span key={partIdx}>{part}</span>;
                                        } else if (part.type === 'link') {
                                            return (
                                                <a
                                                    key={partIdx}
                                                    href={part.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="post-content-link"
                                                >
                                                    {part.text}
                                                </a>
                                            );
                                        }
                                        return null;
                                    })}
                                </p>
                            );
                        })}
                    </div>
                );
            })()}

            {/* Display link previews */}
            {linkPreviews.length > 0 && (
                <div className="link-previews-container">
                    {linkPreviews.map((linkPreview, idx) => (
                        <div 
                            key={idx}
                            className={`link-preview-container link-preview-${linkPreview.provider?.toLowerCase().replace(/\s+/g, '-') || 'default'}`}
                            onClick={(e) => {
                                e.stopPropagation();
                                if (linkPreview.url) {
                                    window.open(linkPreview.url, '_blank', 'noopener,noreferrer');
                                }
                            }}
                        >
                            {linkPreview.thumbnail_url && (
                                <div className="link-preview-image">
                                    <img 
                                        src={linkPreview.thumbnail_url} 
                                        alt={linkPreview.title || 'Link preview'}
                                        onError={(e) => {
                                            e.target.style.display = 'none';
                                        }}
                                    />
                                </div>
                            )}
                            <div className="link-preview-content">
                                <div className="link-preview-provider">
                                    {linkPreview.provider || 'Link'}
                                </div>
                                {linkPreview.title && (
                                    <div className="link-preview-title">
                                        {sanitizeText(linkPreview.title)}
                                    </div>
                                )}
                                {linkPreview.description && (
                                    <div className="link-preview-description">
                                        {sanitizeText(linkPreview.description)}
                                    </div>
                                )}
                                {linkPreview.author_name && (
                                    <div className="link-preview-author">
                                        {sanitizeText(linkPreview.author_name)}
                                    </div>
                                )}
                            </div>
                        </div>
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

            {/* Comments and Reactions section */}
            <div className="comments-section" ref={commentsSectionRef}>
                <div className="comments-reactions-row">
                    {/* Comments button with speech bubble icon */}
                    <button
                        className="comments-toggle-button-icon"
                        onClick={handleToggleComments}
                        aria-expanded={commentsExpanded}
                        title="Comments"
                    >
                        <MessageCircle size={18} />
                        {commentCount > 0 && (
                            <span className="comments-count">{commentCount}</span>
                        )}
                        {(localNotificationSummary.has_unread_comments || localNotificationSummary.has_unread_replies) && (
                            <span className="notification-dot"></span>
                        )}
                    </button>

                    {/* Emoji reaction button */}
                    <div className="emoji-reaction-container" ref={emojiPickerRef}>
                        <button
                            className="emoji-reaction-button"
                            onClick={() => {
                                // Only open picker if long press didn't trigger
                                if (!showingReactors) {
                                    setEmojiPickerOpen(!emojiPickerOpen);
                                }
                            }}
                            onMouseDown={handleReactIconMouseDown}
                            onMouseUp={handleReactIconMouseUp}
                            onMouseLeave={handleReactIconMouseLeave}
                            onTouchStart={handleReactIconTouchStart}
                            onTouchEnd={handleReactIconTouchEnd}
                            onTouchCancel={handleReactIconTouchCancel}
                            title="React with emoji (hold to see who reacted)"
                        >
                            <Smile size={18} />
                        </button>

                        {/* Display grouped reactions with counts */}
                        {Object.keys(groupedReactions).length > 0 && (
                            <div className="reactions-display">
                                {Object.values(groupedReactions).map((group) => {
                                    const isOwnReaction = group.userReacted;
                                    // Find the user's reaction in this group
                                    const userReaction = group.reactions.find(r => r.user_id === currentUser?.id);
                                    return (
                                        <button
                                            key={group.emoji}
                                            className={`reaction-emoji-button ${isOwnReaction ? 'user-reacted' : ''}`}
                                            onClick={() => userReaction ? handleReactionClick(userReaction) : handleEmojiClick(group.emoji)}
                                            title={isOwnReaction ? `Your reaction (${group.count} total) - click to remove` : `${group.count} ${group.emoji}`}
                                        >
                                            <span className="reaction-emoji">{group.emoji}</span>
                                            {group.count > 1 && (
                                                <span className="reaction-count">{group.count}</span>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        )}

                        {/* Emoji picker popup */}
                        {emojiPickerOpen && (
                            <div className="emoji-picker-popup">
                                <div className="emoji-picker-grid">
                                    {popularEmojis.map((emoji) => (
                                        <button
                                            key={emoji}
                                            className="emoji-picker-item"
                                            onClick={() => handleEmojiClick(emoji)}
                                            title={emoji}
                                        >
                                            {emoji}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Reactors modal (shown on long press of react icon) */}
                        {showingReactors !== null && (
                            <div className="reactors-modal-overlay" onClick={() => setShowingReactors(null)}>
                                <div className="reactors-modal" onClick={(e) => e.stopPropagation()}>
                                    <div className="reactors-modal-header">
                                        <span className="reactors-modal-title">Reactions</span>
                                        <button
                                            className="reactors-modal-close"
                                            onClick={() => setShowingReactors(null)}
                                        >
                                            ×
                                        </button>
                                    </div>
                                    {loadingReactors ? (
                                        <div className="reactors-loading">Loading...</div>
                                    ) : showingReactors.length > 0 ? (
                                        <div className="reactors-list">
                                            {showingReactors.map((item, index) => (
                                                <div key={index} className="reactor-item">
                                                    <span className="reactor-emoji">{item.emoji}</span>
                                                    <span className="reactor-name">
                                                        @{item.user.username}
                                                        {item.user.display_name && (
                                                            <span className="reactor-display-name"> ({item.user.display_name})</span>
                                                        )}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="reactors-empty">No mutual connections have reacted</div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
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
