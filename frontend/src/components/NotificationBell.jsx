import { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import { Bell } from "lucide-react";

export default function NotificationBell() {
    const { token } = useAuth();
    const [unreadPostIds, setUnreadPostIds] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(false);
    const pressTimerRef = useRef(null);
    const isPressingRef = useRef(false);

    // Fetch recent notifications
    const fetchNotifications = async () => {
        if (!token) return;
        
        try {
            const data = await api.getRecentNotifications(token, 50);
            setUnreadPostIds(data.unread_post_ids || []);
            // Reset index when notifications change
            if (data.unread_post_ids && data.unread_post_ids.length > 0) {
                setCurrentIndex(0);
            }
        } catch (err) {
            console.error("Failed to fetch notifications", err);
        }
    };

    useEffect(() => {
        fetchNotifications();
        
        // Listen for refresh events from PostCard/Feed
        const handleRefresh = () => {
            fetchNotifications();
        };
        
        window.addEventListener('notification-refresh', handleRefresh);
        
        // Poll for updates every 30 seconds
        const interval = setInterval(fetchNotifications, 30000);
        
        return () => {
            window.removeEventListener('notification-refresh', handleRefresh);
            clearInterval(interval);
        };
    }, [token]);

    // Handle click - jump to next notification
    const handleClick = () => {
        if (unreadPostIds.length === 0 || loading) return;
        
        const postId = unreadPostIds[currentIndex];
        if (!postId) return;
        
        setLoading(true);
        
        // Dispatch event to Feed to jump to post
        window.dispatchEvent(new CustomEvent('jump-to-post', {
            detail: { postId, onComplete: () => setLoading(false) }
        }));
        
        // Move to next notification (or wrap around)
        setCurrentIndex((prev) => {
            const next = prev + 1;
            return next >= unreadPostIds.length ? 0 : next;
        });
    };

    // Handle long-press (1000ms) - clear all recent notifications
    const handleMouseDown = () => {
        isPressingRef.current = true;
        pressTimerRef.current = setTimeout(async () => {
            if (isPressingRef.current && token) {
                try {
                    await api.clearRecentNotifications(token);
                    setUnreadPostIds([]);
                    setCurrentIndex(0);
                    // Dispatch refresh event
                    window.dispatchEvent(new CustomEvent('notification-refresh'));
                } catch (err) {
                    console.error("Failed to clear notifications", err);
                }
            }
        }, 1000);
    };

    const handleMouseUp = () => {
        isPressingRef.current = false;
        if (pressTimerRef.current) {
            clearTimeout(pressTimerRef.current);
            pressTimerRef.current = null;
        }
    };

    const handleMouseLeave = () => {
        isPressingRef.current = false;
        if (pressTimerRef.current) {
            clearTimeout(pressTimerRef.current);
            pressTimerRef.current = null;
        }
    };

    // Touch events for mobile
    const handleTouchStart = () => {
        handleMouseDown();
    };

    const handleTouchEnd = () => {
        handleMouseUp();
    };

    const hasNotifications = unreadPostIds.length > 0;

    return (
        <button
            className={`bell-button ${!hasNotifications ? 'bell-disabled' : ''} ${loading ? 'bell-loading' : ''} bell-appear`}
            onClick={handleClick}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            disabled={!hasNotifications || loading}
            aria-label={hasNotifications ? `Jump to notification (${unreadPostIds.length} unread)` : "No notifications"}
            title={hasNotifications ? `Click to jump to notification. Hold to clear all.` : "No notifications"}
        >
            <Bell size={20} />
            {hasNotifications && <span className="bell-dot"></span>}
        </button>
    );
}
