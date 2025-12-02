# Intentional Social

A calm, human-scale social platform intentionally designed to nurture meaningful relationships rather than maximize reach, engagement, or virality.

## 🌟 Vision

**"Relationship OS"** — The opposite of algorithmic dopamine factories.

- **No Algorithmic Feeds**: Chronological posts only.
- **Human Scale**: Hard limit of **100 follows** per user. Scarcity forces intentionality.
- **Privacy First**: No ads, no tracking.
- **Emotional Depth**: Prioritizing connection over scale.

## 🏗️ Technical Foundation

Built with clean, modern, production-aligned patterns.

### Backend Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL 16 (Dockerized)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Auth**: JWT (OAuth2 with Password Bearer)
- **Validation**: Pydantic

## ✅ Progress So Far

### 1. Infrastructure & Core
- [x] **Project Structure**: Scalable `app/` layout with routers, schemas, and models.
- [x] **Database**: PostgreSQL connected, Alembic migrations initialized.
- [x] **Configuration**: Environment-based settings via `pydantic-settings`.

### 2. Authentication & Security
- [x] **User Model**: Secure password hashing (bcrypt).
- [x] **JWT Auth**: Token generation, verification, and dependency injection (`get_current_user`).
- [x] **Registration/Login**: Fully implemented endpoints.

### 3. Social Features
- [x] **Follow System**: 
    - Follow/Unfollow logic.
    - **100 Follow Limit** enforced.
    - Self-follow and duplicate checks.
- [x] **Posts**: Create text-based posts.
- [x] **Feed**: Chronological feed of followed users' posts with pagination.

### 4. Quality & Fixes
- [x] **Dependencies**: Fixed circular/duplicate dependency issues in `core`.
- [x] **Imports**: Verified package structure and imports.

## 🚀 Next Steps

1.  **Seed Data**: Run the seed script to populate users and content.
    ```bash
    python scripts/seed.py
    ```
2.  **Integration Testing**: Verify auth flows, follow limits, and feed ordering.
3.  **Dockerization**: Containerize the FastAPI application for deployment.
4.  **MVP Deployment**: Deploy to a PaaS (Render/Fly.io) for initial user testing.

## 📂 Project Structure

```
backend/
├── app/
│   ├── core/       # Security, Config, Deps
│   ├── models/     # SQLAlchemy Models (User, Follow, Post)
│   ├── routers/    # API Endpoints (Auth, Feed, Follows, Posts)
│   ├── schemas/    # Pydantic Schemas
│   ├── db.py       # Database Session
│   └── main.py     # App Entrypoint
├── migrations/     # Alembic Migrations
├── scripts/        # Utility Scripts (Seeding)
└── requirements.txt
```
