"""Post service for centralized post business logic."""
from typing import List
from sqlalchemy.orm import Session
from app.models.post import Post
from app.models.user import User
from app.models.post_audience_tag import PostAudienceTag
from app.models.user_tag import UserTag
from app.models.tag import Tag


class PostService:
    """Centralized post business logic."""
    
    @staticmethod
    def filter_posts_by_audience(
        posts: List[Post],
        current_user: User,
        db: Session
    ) -> List[Post]:
        """
        Filter posts based on audience settings.
        
        Rules:
        - Always show own posts
        - Show posts with audience_type='all'
        - Hide private posts from others
        - For tag-based audience, check if user has required tags
        """
        filtered_posts = []
        
        for post in posts:
            # Own posts
            if post.author_id == current_user.id:
                filtered_posts.append(post)
                continue
            
            # Public posts
            if post.audience_type == 'all':
                filtered_posts.append(post)
                continue
            
            # Private posts
            if post.audience_type == 'private':
                continue
            
            # Tag-based audience
            if post.audience_type == 'tags':
                if PostService._user_has_required_tags(
                    post, current_user, db
                ):
                    filtered_posts.append(post)
        
        return filtered_posts
    
    @staticmethod
    def _user_has_required_tags(
        post: Post,
        current_user: User,
        db: Session
    ) -> bool:
        """Check if user has any of the post's required tags."""
        post_tag_ids = (
            db.query(PostAudienceTag.tag_id)
            .filter(PostAudienceTag.post_id == post.id)
            .all()
        )
        
        if not post_tag_ids:
            return True  # No tags = public
        
        post_tag_ids = [t[0] for t in post_tag_ids]
        
        user_has_tag = (
            db.query(UserTag.tag_id)
            .filter(
                UserTag.owner_user_id == post.author_id,
                UserTag.target_user_id == current_user.id,
                UserTag.tag_id.in_(post_tag_ids)
            )
            .first()
        )
        
        return user_has_tag is not None
    
    @staticmethod
    def batch_load_audience_tags(
        posts: List[Post],
        db: Session
    ) -> dict:
        """
        Load audience tags for multiple posts in 2 queries.
        Returns: {post_id: [Tag, Tag, ...]}
        """
        post_ids = [post.id for post in posts]
        
        # Query 1: Get all post-tag associations
        audience_tags_map = {}
        if post_ids:
            associations = (
                db.query(PostAudienceTag)
                .filter(PostAudienceTag.post_id.in_(post_ids))
                .all()
            )
            for assoc in associations:
                if assoc.post_id not in audience_tags_map:
                    audience_tags_map[assoc.post_id] = []
                audience_tags_map[assoc.post_id].append(assoc.tag_id)
        
        # Query 2: Get all tags
        all_tag_ids = set()
        for tag_ids in audience_tags_map.values():
            all_tag_ids.update(tag_ids)
        
        tags_map = {}
        if all_tag_ids:
            tags = db.query(Tag).filter(Tag.id.in_(all_tag_ids)).all()
            tags_map = {tag.id: tag for tag in tags}
        
        # Build final result
        result = {}
        for post_id, tag_ids in audience_tags_map.items():
            result[post_id] = [tags_map[tid] for tid in tag_ids if tid in tags_map]
        
        return result
