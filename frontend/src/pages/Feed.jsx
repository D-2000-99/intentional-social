import { useState, useEffect } from "react";
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

    const handlePost = async (e) => {
        e.preventDefault();
        if (!content.trim()) return;

        try {
            await api.request("/posts/", "POST", {
                content,
                audience_type: audience.audience_type,
                audience_tag_ids: audience.audience_tag_ids,
            }, token);
            setContent("");
            setAudience({ audience_type: 'all', audience_tag_ids: [] });
            fetchFeed(selectedTagIds); // Refresh feed
        } catch (err) {
            alert("Failed to post");
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
                    <div className="post-actions">
                        <AudienceSelector onAudienceChange={setAudience} />
                        <button type="submit">
                            Post
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
                            <p className="post-content">{post.content}</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
