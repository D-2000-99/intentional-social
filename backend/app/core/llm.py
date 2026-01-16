"""
LLM Integration Module for Digest Feature

This module handles AI-generated summaries for posts in the Digest view.
Uses OpenAI's API to generate third-person, factual observations about posts.

Important: This module is designed to be calm, non-judgmental, and factual.
It should never rank, compare, or create urgency.
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Placeholder for OpenAI API key - should be set via environment variable
OPENAI_API_KEY: Optional[str] = None


def generate_digest_summary(
    post_content: str,
    author_name: str,
    photo_count: int = 0,
    timestamp: Optional[str] = None
) -> tuple[str, float]:
    """
    Generate a digest summary and importance score for a post.
    
    Args:
        post_content: The text content of the post
        author_name: The name of the post author
        photo_count: Number of photos in the post
        timestamp: ISO timestamp of the post (optional)
    
    Returns:
        tuple: (summary: str, importance_score: float)
            - summary: Third-person, factual observation (e.g., "Sarah enjoyed matcha on a quiet afternoon.")
            - importance_score: Internal score 0-10 (never exposed to users)
    
    Rules:
        - Summary must be third-person
        - Use the person's name
        - No emotional inference unless explicitly stated
        - No exaggeration or editorial judgment
        - Default to neutral, factual phrasing for sensitive content
    """
    # TODO: Implement OpenAI API integration
    # For now, return placeholder summaries
    
    logger.info(f"Generating digest summary for post by {author_name} (placeholder)")
    
    # Placeholder logic - will be replaced with actual OpenAI API call
    if post_content:
        # Simple placeholder: use first sentence or first 50 chars
        content_preview = post_content.split('.')[0][:50] if '.' in post_content else post_content[:50]
        placeholder_summary = f"{author_name} shared: {content_preview}."
    else:
        placeholder_summary = f"{author_name} shared a moment."
    
    # Placeholder importance score (randomized for demo, but will be AI-generated)
    import random
    placeholder_importance = random.uniform(3.0, 7.0)
    
    return placeholder_summary, placeholder_importance


def generate_weekly_summary(posts_with_scores: list[dict]) -> str:
    """
    Generate a weekly highlight summary based on posts and their importance scores.
    
    Args:
        posts_with_scores: List of dicts with 'importance_score' and optionally 'summary'
    
    Returns:
        str: Gentle, pattern-based observation (e.g., "It was a quieter week overall.")
    
    Rules:
        - Pattern-based, not event-based
        - No scores, labels, or names highlighted
        - Short and gentle
        - May be omitted if week is very quiet
    """
    # TODO: Implement OpenAI API integration for weekly summary
    # For now, return placeholder based on average importance
    
    if not posts_with_scores:
        return None  # Omit summary for empty weeks
    
    avg_importance = sum(p.get('importance_score', 5.0) for p in posts_with_scores) / len(posts_with_scores)
    
    # Placeholder logic
    if avg_importance > 6:
        return "It was an eventful week. Several significant moments stood out among your connections."
    elif avg_importance > 4:
        return "A balanced week. Your friends and family shared a mix of daily routines and small joys."
    else:
        return "It was a quieter week overall. The focus seemed to be on rest, reflection, and small, peaceful moments."


def process_post_digest(post_id: int, db_session) -> None:
    """
    Process a single post to generate its digest summary and importance score.
    This is called by an external digest processing service for each post in the current week.
    
    Args:
        post_id: The ID of the post to process
        db_session: SQLAlchemy database session
    """
    from app.models.post import Post
    
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if not post:
        logger.warning(f"Post {post_id} not found for digest processing")
        return
    
    # Generate summary and score
    summary, importance = generate_digest_summary(
        post_content=post.content,
        author_name=post.author.get_display_name(),
        photo_count=len(post.photo_urls) if post.photo_urls else 0,
        timestamp=post.created_at.isoformat() if post.created_at else None
    )
    
    # Update post with digest data
    post.digest_summary = summary
    post.importance_score = importance
    
    db_session.commit()
    logger.info(f"Processed digest for post {post_id}: importance={importance:.1f}")


# Future OpenAI integration structure (commented out for now)
"""
import openai

async def generate_digest_summary_openai(
    post_content: str,
    author_name: str,
    photo_count: int = 0,
    timestamp: Optional[str] = None
) -> tuple[str, float]:
    \"\"\"
    Actual OpenAI implementation (to be enabled when API key is configured).
    \"\"\"
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f\"\"\"
    You are generating a brief, factual observation about a social media post for a weekly digest.
    
    Post content: {post_content}
    Author: {author_name}
    Photos: {photo_count}
    Time: {timestamp}
    
    Generate:
    1. A single sentence, third-person observation using the person's name.
    2. An importance score (0-10) for internal use only.
    
    Rules:
    - Be factual and neutral
    - Use third person: "{author_name} [action]"
    - No emotional inference unless explicitly stated in content
    - No exaggeration or judgment
    - For sensitive/ambiguous content, default to neutral phrasing
    
    Format your response as JSON:
    {{
        "summary": "...",
        "importance": 0-10
    }}
    \"\"\"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or gpt-4 for better quality
        messages=[
            {"role": "system", "content": "You are a calm, factual observer. Generate brief, third-person summaries."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,  # Lower temperature for more consistent, factual output
        max_tokens=150
    )
    
    # Parse response and return
    # ... implementation details ...
"""

