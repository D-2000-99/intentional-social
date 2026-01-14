import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function DigestView({ onSwitchToNow }) {
    const [digestData, setDigestData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [tagFilter, setTagFilter] = useState("all");
    const scrollContainerRef = useRef(null);
    const { token } = useAuth();

    useEffect(() => {
        fetchDigest();
    }, [token, tagFilter]);

    const fetchDigest = async () => {
        try {
            setLoading(true);
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
                    {["all", "friends", "family"].map((filter) => (
                        <button
                            key={filter}
                            onClick={() => setTagFilter(filter)}
                            className={`digest-filter-chip ${tagFilter === filter ? "active" : ""}`}
                        >
                            {filter.charAt(0).toUpperCase() + filter.slice(1)}
                        </button>
                    ))}
                </div>
                <div className="digest-empty-state">
                    <div className="digest-page">
                        <div className="digest-empty-content">
                            <p className="digest-empty-icon">☕</p>
                            <h3 className="digest-empty-title">A Quiet Week</h3>
                            <p className="digest-empty-text">
                                No updates from your {tagFilter === "all" ? "connections" : tagFilter} circle this week.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const posts = digestData.posts;
    const weeklySummary = digestData.weekly_summary;

    return (
        <div className="digest-container">
            {/* Filter Bar */}
            <div className="digest-filter-bar">
                {["all", "friends", "family"].map((filter) => (
                    <button
                        key={filter}
                        onClick={() => setTagFilter(filter)}
                        className={`digest-filter-chip ${tagFilter === filter ? "active" : ""}`}
                    >
                        {filter.charAt(0).toUpperCase() + filter.slice(1)}
                    </button>
                ))}
            </div>

            {/* Horizontal Scroll Container */}
            <div className="digest-scroll-container" ref={scrollContainerRef}>
                {/* Post Pages */}
                {posts.map((post) => {
                    const dayLabel = formatDayLabel(post.created_at);
                    const firstPhoto = post.photo_urls_presigned?.[0] || null;
                    const summary = post.digest_summary || `${post.author.display_name || post.author.username} shared a moment.`;

                    return (
                        <div key={post.id} className="digest-page">
                            {/* Printed Header */}
                            <div className="digest-header">
                                <span className="digest-day-label">{dayLabel}</span>
                            </div>

                            {/* Content Card */}
                            <div className="digest-content">
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

                                {/* LLM Observation */}
                                <div className="digest-summary">
                                    <p className="digest-summary-text">{summary}</p>
                                    <div className="digest-summary-divider"></div>
                                </div>
                            </div>

                            {/* Pagination Hint */}
                            <div className="digest-footer">
                                <span className="digest-mode-hint">Digest Mode</span>
                            </div>
                        </div>
                    );
                })}

                {/* Summary Page (Last Page) */}
                {weeklySummary && (
                    <div className="digest-page digest-summary-page">
                        <div className="digest-summary-content">
                            <h2 className="digest-summary-title">Weekly Reflection</h2>
                            
                            <p className="digest-summary-body">{weeklySummary}</p>

                            <div className="digest-summary-divider-full"></div>

                            <p className="digest-summary-end">That's all for this week.</p>
                            
                            <button 
                                onClick={onSwitchToNow}
                                className="digest-return-button"
                            >
                                Return to Home
                            </button>
                        </div>
                    </div>
                )}

                {/* End message if no weekly summary */}
                {!weeklySummary && (
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
                )}
            </div>
        </div>
    );
}

