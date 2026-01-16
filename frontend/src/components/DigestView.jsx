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
        const date = new Date(dateString);
        const days = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];
        const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
        
        const dayName = days[date.getUTCDay()];
        const month = months[date.getUTCMonth()];
        const day = date.getUTCDate();
        
        return `${dayName} · ${month} ${day}`;
    };

    const formatDayShort = (dateString) => {
        const date = new Date(dateString);
        const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        return days[date.getUTCDay()];
    };

    const getDayKey = (dateString) => {
        const date = new Date(dateString);
        return date.toISOString().split('T')[0]; // YYYY-MM-DD format
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
                            {uniqueDays.map((day) => (
                                <button
                                    key={day.date}
                                    className="digest-day-jump-item"
                                    onClick={() => jumpToDay(day.postIndex)}
                                >
                                    <span className="digest-day-jump-short">{day.shortLabel}</span>
                                    <span className="digest-day-jump-full">{day.label}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Horizontal Scroll Container */}
            <div className="digest-scroll-container" ref={scrollContainerRef}>
                {/* Post Pages */}
                {posts.map((post) => {
                    const dayLabel = formatDayLabel(post.created_at);
                    const firstPhoto = post.photo_urls_presigned?.[0] || null;
                    const username = post.author.display_name || post.author.username;
                    const caption = post.content || "";

                    return (
                        <div key={post.id} className="digest-page">
                            {/* Printed Header */}
                            <div className="digest-header">
                                <span className="digest-day-label">{dayLabel}</span>
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

