"""Notification service for centralized notification business logic."""
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timezone

from app.models.notification import Notification
from app.models.post import Post
from app.models.comment import Comment
from app.models.reply import Reply
from app.models.user import User
from app.services.connection_service import ConnectionService


class NotificationService:
    """Centralized notification business logic."""
    
    @staticmethod
    def create_comment_notification(
        db: Session,
        post_id: int,
        comment_author_id: int,
    ) -> Optional[Notification]:
        """
        Create a notification when someone comments on a post.
        Notifies the post author (unless they commented on their own post).
        """
        # Get post to find author
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return None
        
        # Don't notify if commenter is the post author
        if post.author_id == comment_author_id:
            return None
        
        # Check if notification already exists (avoid duplicates)
        existing = db.query(Notification).filter(
            Notification.recipient_id == post.author_id,
            Notification.post_id == post_id,
            Notification.type == 'comment',
            Notification.read_at.is_(None)
        ).first()
        
        if existing:
            # Update actor to latest commenter
            existing.actor_id = comment_author_id
            existing.created_at = datetime.now(timezone.utc)
            db.commit()
            return existing
        
        # Create new notification
        notification = Notification(
            recipient_id=post.author_id,
            actor_id=comment_author_id,
            post_id=post_id,
            comment_id=None,
            type='comment',
            created_at=datetime.now(timezone.utc)
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification
    
    @staticmethod
    def create_reply_notifications(
        db: Session,
        comment_id: int,
        reply_author_id: int,
    ) -> List[Notification]:
        """
        Create notifications when someone replies to a comment.
        Notifies:
        - The comment author (unless they replied to themselves)
        - The post author (for replies on any comment of their post)
        - All previous reply participants in the thread (unless they are the reply author)
        """
        # Get comment and post
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            return []
        
        post = db.query(Post).filter(Post.id == comment.post_id).first()
        if not post:
            return []
        
        notifications = []
        notified_user_ids = set()
        
        # 1. Notify comment author (unless they replied to themselves)
        if comment.author_id != reply_author_id:
            notified_user_ids.add(comment.author_id)
            # Check for existing unread notification
            existing = db.query(Notification).filter(
                Notification.recipient_id == comment.author_id,
                Notification.comment_id == comment_id,
                Notification.type == 'reply',
                Notification.read_at.is_(None)
            ).first()
            
            if existing:
                existing.actor_id = reply_author_id
                existing.created_at = datetime.now(timezone.utc)
            else:
                notification = Notification(
                    recipient_id=comment.author_id,
                    actor_id=reply_author_id,
                    post_id=post.id,
                    comment_id=comment_id,
                    type='reply',
                    created_at=datetime.now(timezone.utc)
                )
                db.add(notification)
                notifications.append(notification)
        
        # 2. Notify post author (unless they are the reply author)
        if post.author_id != reply_author_id and post.author_id not in notified_user_ids:
            notified_user_ids.add(post.author_id)
            # Check for existing unread notification
            existing = db.query(Notification).filter(
                Notification.recipient_id == post.author_id,
                Notification.post_id == post.id,
                Notification.type == 'reply',
                Notification.read_at.is_(None)
            ).first()
            
            if existing:
                existing.actor_id = reply_author_id
                existing.created_at = datetime.now(timezone.utc)
            else:
                notification = Notification(
                    recipient_id=post.author_id,
                    actor_id=reply_author_id,
                    post_id=post.id,
                    comment_id=comment_id,
                    type='reply',
                    created_at=datetime.now(timezone.utc)
                )
                db.add(notification)
                notifications.append(notification)
        
        # 3. Notify all previous reply participants in this comment thread
        previous_replies = db.query(Reply).filter(
            Reply.comment_id == comment_id,
            Reply.author_id != reply_author_id  # Exclude current reply author
        ).all()
        
        for prev_reply in previous_replies:
            if prev_reply.author_id not in notified_user_ids:
                notified_user_ids.add(prev_reply.author_id)
                # Check for existing unread notification
                existing = db.query(Notification).filter(
                    Notification.recipient_id == prev_reply.author_id,
                    Notification.comment_id == comment_id,
                    Notification.type == 'reply',
                    Notification.read_at.is_(None)
                ).first()
                
                if existing:
                    existing.actor_id = reply_author_id
                    existing.created_at = datetime.now(timezone.utc)
                else:
                    notification = Notification(
                        recipient_id=prev_reply.author_id,
                        actor_id=reply_author_id,
                        post_id=post.id,
                        comment_id=comment_id,
                        type='reply',
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(notification)
                    notifications.append(notification)
        
        if notifications:
            db.commit()
            for notif in notifications:
                db.refresh(notif)
        
        return notifications
    
    @staticmethod
    def get_post_notification_summary(
        db: Session,
        user_id: int,
        post_ids: List[int],
    ) -> Dict[int, Dict[str, bool]]:
        """
        Get notification summary for multiple posts.
        Returns: {post_id: {'has_unread_comments': bool, 'has_unread_replies': bool}}
        """
        if not post_ids:
            return {}
        
        # Query unread notifications for these posts
        unread_notifications = db.query(Notification).filter(
            Notification.recipient_id == user_id,
            Notification.post_id.in_(post_ids),
            Notification.read_at.is_(None)
        ).all()
        
        # Build summary
        summary = {post_id: {'has_unread_comments': False, 'has_unread_replies': False} for post_id in post_ids}
        
        for notif in unread_notifications:
            if notif.type == 'comment':
                summary[notif.post_id]['has_unread_comments'] = True
            elif notif.type == 'reply':
                summary[notif.post_id]['has_unread_replies'] = True
        
        return summary
    
    @staticmethod
    def get_comment_notification_summary(
        db: Session,
        user_id: int,
        comment_ids: List[int],
    ) -> Dict[int, bool]:
        """
        Get notification summary for multiple comments.
        Returns: {comment_id: has_unread_reply}
        """
        if not comment_ids:
            return {}
        
        # Query unread reply notifications for these comments
        unread_notifications = db.query(Notification).filter(
            Notification.recipient_id == user_id,
            Notification.comment_id.in_(comment_ids),
            Notification.type == 'reply',
            Notification.read_at.is_(None)
        ).all()
        
        # Build summary
        summary = {comment_id: False for comment_id in comment_ids}
        for notif in unread_notifications:
            if notif.comment_id:
                summary[notif.comment_id] = True
        
        return summary
    
    @staticmethod
    def get_recent_feed_post_ids(
        db: Session,
        current_user: User,
        limit: int = 50,
    ) -> List[int]:
        """
        Get the IDs of the most recent N posts in the user's feed.
        Uses the same connection filtering as the feed endpoint.
        """
        # Get connected user IDs (same logic as feed)
        connected_user_ids = ConnectionService.get_connected_user_ids(
            current_user, db, include_self=True
        )
        
        if not connected_user_ids:
            return []
        
        # Get recent post IDs (just IDs, not full posts)
        post_ids = (
            db.query(Post.id)
            .filter(Post.author_id.in_(connected_user_ids))
            .order_by(Post.created_at.desc())
            .limit(limit)
            .all()
        )
        
        return [pid[0] for pid in post_ids]
    
    @staticmethod
    def get_recent_unread_post_ids(
        db: Session,
        user_id: int,
        recent_post_ids: List[int],
    ) -> List[int]:
        """
        Get post IDs from recent_post_ids that have unread notifications,
        ordered by newest notification first.
        """
        if not recent_post_ids:
            return []
        
        # Get unread notifications for recent posts, ordered by newest first
        # Need to include created_at in SELECT for ORDER BY to work with DISTINCT in PostgreSQL
        unread_notifications = (
            db.query(Notification.post_id, Notification.created_at)
            .filter(
                Notification.recipient_id == user_id,
                Notification.post_id.in_(recent_post_ids),
                Notification.read_at.is_(None)
            )
            .order_by(Notification.created_at.desc())
            .all()
        )
        
        # Extract unique post IDs (maintaining order by newest notification first)
        seen = set()
        result = []
        for post_id, created_at in unread_notifications:
            if post_id not in seen:
                seen.add(post_id)
                result.append(post_id)
        
        return result
    
    @staticmethod
    def mark_post_notifications_read(
        db: Session,
        user_id: int,
        post_id: int,
    ) -> int:
        """
        Mark all unread notifications for a post as read.
        Returns count of notifications marked.
        """
        now = datetime.now(timezone.utc)
        count = (
            db.query(Notification)
            .filter(
                Notification.recipient_id == user_id,
                Notification.post_id == post_id,
                Notification.read_at.is_(None)
            )
            .update({'read_at': now}, synchronize_session=False)
        )
        db.commit()
        return count
    
    @staticmethod
    def mark_comment_notifications_read(
        db: Session,
        user_id: int,
        comment_id: int,
    ) -> int:
        """
        Mark all unread reply notifications for a comment as read.
        Returns count of notifications marked.
        """
        now = datetime.now(timezone.utc)
        count = (
            db.query(Notification)
            .filter(
                Notification.recipient_id == user_id,
                Notification.comment_id == comment_id,
                Notification.type == 'reply',
                Notification.read_at.is_(None)
            )
            .update({'read_at': now}, synchronize_session=False)
        )
        db.commit()
        return count
    
    @staticmethod
    def clear_recent_notifications(
        db: Session,
        user_id: int,
        recent_post_ids: List[int],
    ) -> int:
        """
        Mark all unread notifications for recent posts as read.
        Returns count of notifications cleared.
        """
        if not recent_post_ids:
            return 0
        
        now = datetime.now(timezone.utc)
        count = (
            db.query(Notification)
            .filter(
                Notification.recipient_id == user_id,
                Notification.post_id.in_(recent_post_ids),
                Notification.read_at.is_(None)
            )
            .update({'read_at': now}, synchronize_session=False)
        )
        db.commit()
        return count
