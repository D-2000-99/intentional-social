import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PhotoGallery from "./PhotoGallery";

export default function ReportedPostCard({ report, onResolved, onPostDeleted }) {
    const { token } = useAuth();
    const [resolving, setResolving] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleResolve = async () => {
        if (!confirm("Mark this report as resolved?")) {
            return;
        }
        
        setResolving(true);
        try {
            await api.resolveReport(token, report.id);
            if (onResolved) {
                onResolved(report.id);
            }
        } catch (err) {
            alert(`Failed to resolve report: ${err.message}`);
        } finally {
            setResolving(false);
        }
    };

    const handleDeletePost = async () => {
        if (!report.post) {
            return;
        }
        
        if (!confirm("Are you sure you want to delete this post? This action cannot be undone.")) {
            return;
        }
        
        setDeleting(true);
        try {
            await api.deletePost(token, report.post.id);
            if (onPostDeleted) {
                onPostDeleted(report.post.id);
            }
        } catch (err) {
            alert(`Failed to delete post: ${err.message}`);
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className="reported-post-card">
            <div className="post-meta">
                <span>Report ID: #{report.id}</span>
                <span>
                    Reported: {new Date(report.created_at).toLocaleString()}
                </span>
            </div>
            
            {report.reason && (
                <div className="report-meta">
                    <strong>Reason:</strong> {report.reason}
                </div>
            )}
            
            {report.post && (
                <div>
                    <h3>Post Content</h3>
                    <div className="post-meta">
                        <span>
                            Author: {report.post.author?.email || "Unknown"}
                        </span>
                        <span>
                            {new Date(report.post.created_at).toLocaleString()}
                        </span>
                    </div>
                    <div className="post-content">
                        {report.post.content}
                    </div>
                    
                    {/* Display photos if available */}
                    {report.post.photo_urls_presigned && report.post.photo_urls_presigned.length > 0 && (
                        <div className="post-photos">
                            <PhotoGallery photos={report.post.photo_urls_presigned} />
                        </div>
                    )}
                </div>
            )}
            
            {report.reported_by && (
                <div className="post-meta">
                    <span>Reported by: {report.reported_by.email}</span>
                </div>
            )}
            
            {!report.resolved_at && (
                <div className="post-actions">
                    <button
                        className="btn btn-primary"
                        onClick={handleResolve}
                        disabled={resolving || deleting}
                    >
                        {resolving ? "Resolving..." : "Mark as Resolved"}
                    </button>
                    {report.post && (
                        <button
                            className="btn btn-danger"
                            onClick={handleDeletePost}
                            disabled={resolving || deleting}
                        >
                            {deleting ? "Deleting..." : "Delete Post"}
                        </button>
                    )}
                </div>
            )}
            
            {report.resolved_at && (
                <div style={{ color: '#4caf50', marginTop: '10px' }}>
                    ✓ Resolved on {new Date(report.resolved_at).toLocaleString()}
                </div>
            )}
        </div>
    );
}

