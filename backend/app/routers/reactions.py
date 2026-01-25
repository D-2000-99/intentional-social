from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from typing import List, Dict
from collections import defaultdict

from app.core.deps import get_db, get_current_user
from app.models.reaction import Reaction
from app.models.post import Post
from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.schemas.reaction import (
    ReactionCreate,
    ReactionOut,
    ReactionSummary,
    PostReactionsOut,
    EmojiReactorsOut,
    ReactorOut
)

router = APIRouter(prefix="/reactions", tags=["Reactions"])


def are_connected(db: Session, user1_id: int, user2_id: int) -> bool:
    """Check if two users are connected (accepted connection)."""
    user_a_id = min(user1_id, user2_id)
    user_b_id = max(user1_id, user2_id)
    
    connection = (
        db.query(Connection)
        .filter(
            Connection.user_a_id == user_a_id,
            Connection.user_b_id == user_b_id,
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .first()
    )
    return connection is not None


@router.post("/posts/{post_id}", response_model=ReactionOut, status_code=status.HTTP_201_CREATED)
def create_or_update_reaction(
    post_id: int,
    reaction_data: ReactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create or update a reaction to a post.
    Only users connected to the post author can react.
    If user already reacted, update the emoji.
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if user can react (must be connected to post author)
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only react to posts from your connections"
            )
    
    # Validate emoji (basic check - should be a single emoji character)
    if not reaction_data.emoji or len(reaction_data.emoji.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Emoji is required"
        )
    
    # Check if user already reacted to this post
    existing_reaction = (
        db.query(Reaction)
        .filter(
            Reaction.post_id == post_id,
            Reaction.user_id == current_user.id
        )
        .first()
    )
    
    if existing_reaction:
        # Update existing reaction
        existing_reaction.emoji = reaction_data.emoji.strip()
        db.commit()
        db.refresh(existing_reaction)
        # Load user relationship
        existing_reaction.user = current_user
        return existing_reaction
    else:
        # Create new reaction
        new_reaction = Reaction(
            post_id=post_id,
            user_id=current_user.id,
            emoji=reaction_data.emoji.strip()
        )
        db.add(new_reaction)
        db.commit()
        db.refresh(new_reaction)
        # Load user relationship
        new_reaction.user = current_user
        return new_reaction


@router.get("/posts/{post_id}", response_model=List[ReactionOut])
def get_post_reactions(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all individual reactions for a post.
    Returns list of individual reactions (one per user).
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if user can see the post (must be connected to post author)
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view reactions on posts from your connections"
            )
    
    # Get all reactions for this post with user info
    all_reactions = (
        db.query(Reaction)
        .options(joinedload(Reaction.user))
        .filter(Reaction.post_id == post_id)
        .order_by(Reaction.created_at.asc())
        .all()
    )
    
    # Return individual reactions
    return [ReactionOut.from_orm(r) for r in all_reactions]


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_reaction(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove user's reaction from a post.
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Find user's reaction
    reaction = (
        db.query(Reaction)
        .filter(
            Reaction.post_id == post_id,
            Reaction.user_id == current_user.id
        )
        .first()
    )
    
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )
    
    db.delete(reaction)
    db.commit()
    return None


@router.get("/posts/{post_id}/emoji/{emoji}/reactors", response_model=EmojiReactorsOut)
def get_emoji_reactors(
    post_id: int,
    emoji: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of users who reacted with a specific emoji to a post.
    Only shows mutual connections (users connected to both current user and post author).
    Post author can see all reactors.
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if user can see the post (must be connected to post author)
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view reactions on posts from your connections"
            )
    
    # Get all reactions with this emoji
    reactions = (
        db.query(Reaction)
        .options(joinedload(Reaction.user))
        .filter(
            Reaction.post_id == post_id,
            Reaction.emoji == emoji
        )
        .all()
    )
    
    # Filter to show only mutual connections
    # Post author can see all reactors
    is_post_author = (post.author_id == current_user.id)
    
    visible_reactors = []
    for reaction in reactions:
        reactor = reaction.user
        
        # Post author can see all reactors
        if is_post_author:
            visible_reactors.append(ReactorOut(
                id=reactor.id,
                username=reactor.username or "",
                display_name=reactor.display_name,
                full_name=reactor.full_name
            ))
        else:
            # For non-authors: only show if reactor is connected to both current user and post author
            # (i.e., mutual connection)
            is_connected_to_reactor = are_connected(db, current_user.id, reactor.id)
            is_reactor_connected_to_author = are_connected(db, reactor.id, post.author_id)
            
            if is_connected_to_reactor and is_reactor_connected_to_author:
                visible_reactors.append(ReactorOut(
                    id=reactor.id,
                    username=reactor.username or "",
                    display_name=reactor.display_name,
                    full_name=reactor.full_name
                ))
    
    return EmojiReactorsOut(
        emoji=emoji,
        reactors=visible_reactors
    )


@router.get("/posts/{post_id}/reactors")
def get_all_reactors(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all users who reacted to a post with their reactions.
    Only shows mutual connections (users connected to both current user and post author).
    Post author can see all reactors.
    Returns list of {user: ReactorOut, emoji: str}
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if user can see the post (must be connected to post author)
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view reactions on posts from your connections"
            )
    
    # Get all reactions for this post
    all_reactions = (
        db.query(Reaction)
        .options(joinedload(Reaction.user))
        .filter(Reaction.post_id == post_id)
        .all()
    )
    
    # Filter to show only mutual connections
    # Post author can see all reactors
    is_post_author = (post.author_id == current_user.id)
    
    visible_reactors = []
    for reaction in all_reactions:
        reactor = reaction.user
        
        # Post author can see all reactors
        if is_post_author:
            visible_reactors.append({
                "user": {
                    "id": reactor.id,
                    "username": reactor.username or "",
                    "display_name": reactor.display_name,
                    "full_name": reactor.full_name
                },
                "emoji": reaction.emoji
            })
        else:
            # For non-authors: only show if reactor is connected to both current user and post author
            # (i.e., mutual connection)
            is_connected_to_reactor = are_connected(db, current_user.id, reactor.id)
            is_reactor_connected_to_author = are_connected(db, reactor.id, post.author_id)
            
            if is_connected_to_reactor and is_reactor_connected_to_author:
                visible_reactors.append({
                    "user": {
                        "id": reactor.id,
                        "username": reactor.username or "",
                        "display_name": reactor.display_name,
                        "full_name": reactor.full_name
                    },
                    "emoji": reaction.emoji
                })
    
    return visible_reactors
