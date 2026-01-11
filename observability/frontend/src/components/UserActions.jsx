export default function UserActions({ user, onBan, onUnban, onDelete, banning, unbanning, deleting }) {
    return (
        <div className="user-actions">
            {user.is_banned ? (
                <button
                    className="btn btn-secondary"
                    onClick={onUnban}
                    disabled={unbanning}
                >
                    {unbanning ? "..." : "Unban"}
                </button>
            ) : (
                <button
                    className="btn btn-danger"
                    onClick={onBan}
                    disabled={banning}
                >
                    {banning ? "..." : "Ban"}
                </button>
            )}
            <button
                className="btn btn-danger"
                onClick={onDelete}
                disabled={deleting}
            >
                {deleting ? "..." : "Delete"}
            </button>
        </div>
    );
}

