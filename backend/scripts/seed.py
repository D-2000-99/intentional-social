"""
Seed script for intentional_social
Creates sample users, random follows (respecting 100 cap),
and posts so you can feel the social experience.

Run:
    python scripts/seed.py
"""

import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy.orm import Session

from app.db import SessionLocal, Base, engine
from app.models.user import User
from app.models.follow import Follow
from app.models.post import Post
from app.core.security import get_password_hash

# -----------------------------------------
# Config
# -----------------------------------------
NUM_USERS = 15
MAX_FOLLOWS_PER_USER = 100
MIN_POSTS = 2
MAX_POSTS = 6

fake = Faker()


# -----------------------------------------
# Helper Functions
# -----------------------------------------
def create_users(db: Session):
    """Create users only if DB is empty."""
    existing_count = db.query(User).count()
    if existing_count > 0:
        print(f"[SKIP] {existing_count} users already exist.")
        return

    print(f"[CREATE] Creating {NUM_USERS} users...")

    for _ in range(NUM_USERS):
        username = fake.user_name()
        email = f"{username}@example.com"
        password = get_password_hash("password123")

        user = User(
            email=email,
            username=username,
            hashed_password=password,
        )
        db.add(user)

    db.commit()
    print("[DONE] Users created.")


def reset_relationships(db: Session):
    """Wipe follow + posts to keep script idempotent."""
    db.query(Follow).delete()
    db.query(Post).delete()
    db.commit()
    print("[RESET] Cleared follows and posts.")


def seed_follows(db: Session):
    """Random follow relationships with 100 cap."""
    users = db.query(User).all()

    print("[CREATE] Generating follow graph...")

    for user in users:
        followees = users.copy()
        followees.remove(user)

        # choose random number of followees but <= MAX_FOLLOWS_PER_USER
        k = random.randint(2, min(len(followees), MAX_FOLLOWS_PER_USER))
        chosen = random.sample(followees, k=k)

        for followee in chosen:
            rel = Follow(
                follower_id=user.id,
                followee_id=followee.id,
            )
            db.add(rel)

    db.commit()
    print("[DONE] Follows created.")


def seed_posts(db: Session):
    """Each user gets 2–6 posts, with random timestamps."""
    users = db.query(User).all()

    print("[CREATE] Generating posts...")

    for user in users:
        num_posts = random.randint(MIN_POSTS, MAX_POSTS)

        for _ in range(num_posts):
            days_ago = random.randint(0, 30)
            content = fake.sentence(nb_words=random.randint(6, 14))

            post = Post(
                author_id=user.id,
                content=content,
                created_at=datetime.utcnow() - timedelta(days=days_ago),
            )
            db.add(post)

    db.commit()
    print("[DONE] Posts created.")


# -----------------------------------------
# Entrypoint
# -----------------------------------------
def main():
    print("====== SEED START ======")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        create_users(db)
        reset_relationships(db)
        seed_follows(db)
        seed_posts(db)

        print("====== SEED COMPLETE ======")

    finally:
        db.close()


if __name__ == "__main__":
    main()