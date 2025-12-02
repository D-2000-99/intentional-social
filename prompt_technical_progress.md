# Project Context: Intentional Social (Backend MVP)

**Role**: You are an expert Senior Software Architect and Product Strategist.
**Goal**: Review the current state of "Intentional Social", a backend MVP, and provide critical analysis, architectural recommendations, and brainstorming for the next phase.

---

## 1. Vision & Philosophy
**Name**: Intentional Social
**Concept**: A "Relationship OS" designed to nurture meaningful connections, not maximize engagement.
**Core Principles**:
1.  **Human Scale**: Hard limit of **100 follows** per user. Scarcity forces intentionality.
2.  **No Algorithms**: The feed is strictly chronological. No "For You" page, no engagement bait.
3.  **Privacy First**: No ads, no tracking, no data farming.
4.  **Calm Design**: Emotional depth over dopamine loops.

---

## 2. Technical Stack (Backend)
The project is currently a backend-only MVP.

-   **Language**: Python 3.13
-   **Framework**: FastAPI
-   **Database**: PostgreSQL 16 (Dockerized)
-   **ORM**: SQLAlchemy (Sync)
-   **Migrations**: Alembic
-   **Authentication**: OAuth2 (Password Flow) + JWT (HS256)
-   **Validation**: Pydantic
-   **Configuration**: `pydantic-settings` (.env)
-   **Testing**: `pytest`, `httpx`

---

## 3. Current Architecture & Implementation

### Directory Structure
```
backend/
├── app/
│   ├── core/       # Security (JWT, pwd_context), Config, Deps (get_db, get_current_user)
│   ├── models/     # SQLAlchemy Models (User, Follow, Post)
│   ├── routers/    # API Endpoints (Auth, Feed, Follows, Posts)
│   ├── schemas/    # Pydantic Schemas (Request/Response models)
│   ├── db.py       # Database Session (SessionLocal)
│   └── main.py     # App Entrypoint
├── migrations/     # Alembic Migrations
├── scripts/        # Seed script
├── tests/          # Pytest Suite (Auth, Follows, Feed)
└── requirements.txt
```

### Key Features Implemented
1.  **Authentication**:
    -   Registration & Login (Username/Email).
    -   Bcrypt password hashing (Pinned to `bcrypt==3.2.2` due to `passlib` compatibility).
    -   JWT Access Tokens.
2.  **Follow System**:
    -   Enforced **100-follow limit** (Configurable via `MAX_FOLLOWS` in `config.py`).
    -   Prevention of self-follows and duplicates.
    -   Database constraints (Unique `follower_id` + `followee_id`).
3.  **Feed**:
    -   Chronological feed of posts from followed users.
    -   Implemented via subquery: `Post.author_id.in_(followee_subq)`.
    -   Pagination (Limit/Offset).
4.  **Seeding**:
    -   `seed.py` script generates 15 users, random follows, and posts to simulate a live environment.
5.  **Testing**:
    -   Comprehensive `pytest` suite covering Auth, Follow limits, and Feed ordering.

### Database Schema
-   **User**: `id`, `email`, `username`, `hashed_password`, `created_at`.
-   **Follow**: `id`, `follower_id`, `followee_id`, `created_at`. (Indexes on foreign keys).
-   **Post**: `id`, `author_id`, `content`, `created_at`.

---

## 4. Current Status & Known Context
-   **Status**: The MVP is functional. Users can sign up, follow others (up to 100), post, and see their feed.
-   **Infrastructure**: Running locally with `uvicorn` and a Dockerized Postgres instance.
-   **Testing**: Full test suite passing (Auth, Follows, Feed).
-   **Code Quality**: Modular, type-safe (Pydantic), and follows FastAPI best practices.
-   **Documentation**:
    -   `README.md`: Project vision and setup instructions.
    -   `v1_backend_review.md`: Detailed internal quality and architectural review.
-   **Known Limitations**:
    -   Synchronous DB driver (`psycopg2`).
    -   Basic error handling (could use global exception handler).

---

## 5. Request for Review
Based on the above context, please provide:
1.  **Architectural Critique**: Are there potential bottlenecks or flaws in the current "Human Scale" implementation?
2.  **Feature Brainstorming**: How can we further enforce "Intentionality" in the API design? (e.g., decaying follows, interaction limits).
3.  **Next Steps**: Recommendations for moving from MVP to a production-ready alpha (Testing strategies, Deployment, CI/CD).
