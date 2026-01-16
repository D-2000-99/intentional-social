import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { sanitizeText, sanitizeUrlParam } from "../utils/security";

export default function DigestView({ onSwitchToNow }) {
    const [digestData, setDigestData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedTagId, setSelectedTagId] = useState(null);
    const [tags, setTags] = useState([]);
    const [showDayJump, setShowDayJump] = useState(false);
    const scrollContainerRef = useRef(null);
    const { token } = useAuth();

    useEffect(() => {
        fetchTags();
    }, [token]);

    useEffect(() => {
        fetchDigest();
    }, [token, selectedTagId]);

    const fetchTags = async () => {
        try {
            const data = await api.getTags(token);
            setTags(data);
        } catch (err) {
            console.error("Failed to fetch tags", err);
        }
    };

    const fetchDigest = async () => {
        try {
            setLoading(true);
            const tagFilter = selectedTagId ? selectedTagId.toString() : "all";
            const data = await api.getDigest(token, tagFilter);
            setDigestData(data);
        } catch (err) {
            console.error("Failed to fetch digest", err);
        } finally {
            setLoading(false);
        }
    };

    const formatDayLabel = (dateString) => {
        // Parse the date string - handle both timezone-aware and naive timestamps
        // Since we're using client timestamps (naive), parse as local time
        const date = new Date(dateString);
        const days = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];
        const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
        
        // Use local time methods instead of UTC to match client timestamps
        const dayName = days[date.getDay()];
        const month = months[date.getMonth()];
        const day = date.getDate();
        
        return `${dayName} · ${month} ${day}`;
    };

    const formatDayShort = (dateString) => {
        const date = new Date(dateString);
        const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        // Use local time method instead of UTC
        return days[date.getDay()];
    };

    const getDayKey = (dateString) => {
        // Parse date and get local date string (YYYY-MM-DD format)
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    // Group posts by day and get unique days
    const getUniqueDays = () => {
        if (!digestData?.posts) return [];
        const daySet = new Set();
        const dayMap = new Map();
        
        digestData.posts.forEach((post, index) => {
            const dayKey = getDayKey(post.created_at);
            if (!daySet.has(dayKey)) {
                daySet.add(dayKey);
                dayMap.set(dayKey, {
                    date: post.created_at,
                    label: formatDayLabel(post.created_at),
                    shortLabel: formatDayShort(post.created_at),
                    postIndex: index
                });
            }
        });
        
        return Array.from(dayMap.values());
    };

    const jumpToDay = (postIndex) => {
        if (!scrollContainerRef.current) return;
        
        // Get all post page elements (excluding the end page)
        const postPages = Array.from(scrollContainerRef.current.children).filter(
            (child) => !child.classList.contains('digest-summary-page')
        );
        
        const targetPost = postPages[postIndex];
        if (targetPost) {
            targetPost.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
            setShowDayJump(false);
        }
    };

    // Close day jump menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (showDayJump && !event.target.closest('.digest-day-jump-container')) {
                setShowDayJump(false);
            }
        };
        
        if (showDayJump) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }
    }, [showDayJump]);

    if (loading) {
        return (
            <div className="digest-container">
                <p className="loading-state">Loading digest...</p>
            </div>
        );
    }

    if (!digestData || !digestData.posts || digestData.posts.length === 0) {
        return (
            <div className="digest-container">
                <div className="digest-filter-bar">
                    <button
                        onClick={() => setSelectedTagId(null)}
                        className={`digest-filter-chip ${selectedTagId === null ? "active" : ""}`}
                    >
                        All
                    </button>
                    {tags.map((tag) => (
                        <button
                            key={tag.id}
                            onClick={() => setSelectedTagId(tag.id)}
                            className={`digest-filter-chip ${selectedTagId === tag.id ? "active" : ""}`}
                        >
                            {tag.name}
                        </button>
                    ))}
                </div>
                <div className="digest-empty-state">
                    <div className="digest-page">
                        <div className="digest-empty-content">
                            <p className="digest-empty-icon">☕</p>
                            <h3 className="digest-empty-title">A Quiet Week</h3>
                            <p className="digest-empty-text">
                                No updates from your {selectedTagId === null ? "connections" : tags.find(t => t.id === selectedTagId)?.name || "connections"} circle this week.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const posts = digestData.posts;
    const uniqueDays = getUniqueDays();

    // Group posts by day, then separate into image posts and text-only posts per day
    const postsByDay = new Map();
    
    posts.forEach(post => {
        const dayKey = getDayKey(post.created_at);
        if (!postsByDay.has(dayKey)) {
            postsByDay.set(dayKey, {
                date: post.created_at,
                dayLabel: formatDayLabel(post.created_at),
                imagePosts: [],
                textOnlyPosts: []
            });
        }
        
        const dayData = postsByDay.get(dayKey);
        // Check photo_urls (source of truth) rather than just presigned URLs
        if (post.photo_urls && post.photo_urls.length > 0) {
            dayData.imagePosts.push(post);
        } else {
            dayData.textOnlyPosts.push(post);
        }
    });

    // Convert to sorted array of days
    const sortedDays = Array.from(postsByDay.values()).sort((a, b) => 
        new Date(a.date) - new Date(b.date)
    );

    // Calculate page indices for day jump navigation
    let currentPageIndex = 0;
    const dayPageIndices = new Map();
    sortedDays.forEach(day => {
        const dayKey = getDayKey(day.date);
        dayPageIndices.set(dayKey, currentPageIndex);
        // Each image post is a page, plus one page for text-only posts if they exist
        currentPageIndex += day.imagePosts.length + (day.textOnlyPosts.length > 0 ? 1 : 0);
    });

    return (
        <div className="digest-container">
            {/* Filter Bar */}
            <div className="digest-filter-bar">
                <button
                    onClick={() => setSelectedTagId(null)}
                    className={`digest-filter-chip ${selectedTagId === null ? "active" : ""}`}
                >
                    All
                </button>
                {tags.map((tag) => (
                    <button
                        key={tag.id}
                        onClick={() => setSelectedTagId(tag.id)}
                        className={`digest-filter-chip ${selectedTagId === tag.id ? "active" : ""}`}
                    >
                        {tag.name}
                    </button>
                ))}
            </div>

            {/* Day Jump Button */}
            {uniqueDays.length > 1 && (
                <div className="digest-day-jump-container">
                    <button
                        className="digest-day-jump-button"
                        onClick={() => setShowDayJump(!showDayJump)}
                        title="Jump to day"
                    >
                        <span>📅</span>
                    </button>
                    {showDayJump && (
                        <div className="digest-day-jump-menu">
                            {uniqueDays.map((day) => {
                                const dayKey = getDayKey(day.date);
                                const pageIndex = dayPageIndices.get(dayKey);
                                return (
                                    <button
                                        key={day.date}
                                        className="digest-day-jump-item"
                                        onClick={() => pageIndex !== undefined && jumpToDay(pageIndex)}
                                    >
                                        <span className="digest-day-jump-short">{day.shortLabel}</span>
                                        <span className="digest-day-jump-full">{day.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Horizontal Scroll Container */}
            <div className="digest-scroll-container" ref={scrollContainerRef}>
                {/* Render posts grouped by day */}
                {sortedDays.map((day) => (
                    <>
                        {/* Image Posts for this day */}
                        {day.imagePosts.map((post) => {
                            const firstPhoto = post.photo_urls_presigned?.[0] || null;
                            const username = post.author.display_name || post.author.username;
                            const caption = post.content || "";

                            return (
                                <div key={post.id} className="digest-page">
                                    {/* Printed Header */}
                                    <div className="digest-header">
                                        <span className="digest-day-label">{day.dayLabel}</span>
                                    </div>

                                    {/* Content Card */}
                                    <div className="digest-content">
                                        {/* Username */}
                                        <div className="digest-username">
                                            <Link 
                                                to={`/profile/${sanitizeUrlParam(post.author.username || '')}`}
                                                className="digest-username-text digest-username-link"
                                            >
                                                {sanitizeText(username)}
                                            </Link>
                                        </div>

                                        {/* Image */}
                                        {firstPhoto && (
                                            <div className="digest-image-container">
                                                <div className="digest-image-border"></div>
                                                <img 
                                                    src={firstPhoto} 
                                                    alt="Post" 
                                                    className="digest-image"
                                                />
                                            </div>
                                        )}

                                        {/* Caption */}
                                        {caption && (
                                            <div className="digest-caption">
                                                <p className="digest-caption-text">{caption}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}

                        {/* Text-Only Posts for this day */}
                        {day.textOnlyPosts.length > 0 && (
                            <div key={`${day.date}-text`} className="digest-page digest-text-only-page">
                                <div className="digest-text-only-header">
                                    <span className="digest-day-label">{day.dayLabel}</span>
                                </div>
                                <div className="digest-text-only-content">
                                    {day.textOnlyPosts.map((post) => {
                                        const username = post.author.display_name || post.author.username;
                                        const caption = post.content || "";

                                        return (
                                            <div key={post.id} className="digest-text-post-card">
                                                <div className="digest-text-post-header">
                                                    <Link 
                                                        to={`/profile/${sanitizeUrlParam(post.author.username || '')}`}
                                                        className="digest-text-post-username"
                                                    >
                                                        {sanitizeText(username)}
                                                    </Link>
                                                    <span className="digest-text-post-date">
                                                        {new Date(post.created_at).toLocaleTimeString('en-US', { 
                                                            hour: 'numeric', 
                                                            minute: '2-digit',
                                                            hour12: true 
                                                        })}
                                                    </span>
                                                </div>
                                                {caption && (
                                                    <div className="digest-text-post-content">
                                                        <p className="digest-text-post-text">{sanitizeText(caption)}</p>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </>
                ))}

                {/* End Page */}
                <div className="digest-page digest-summary-page">
                    <div className="digest-summary-content">
                        <p className="digest-summary-end">That's all for this week.</p>
                        <button 
                            onClick={onSwitchToNow}
                            className="digest-return-button"
                        >
                            Return to Home
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

