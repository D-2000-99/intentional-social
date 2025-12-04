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

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- PostgreSQL 16+
- Node.js 18+ (for frontend)

### Setup

1. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env  # Configure your environment variables
   alembic upgrade head
   ```

2. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   cp .env.example .env  # Set VITE_API_URL
   npm run dev
   ```

3. **Seed Data (Optional):**
   ```bash
   cd backend
   python seed.py
   ```

### Deployment

See `DEPLOYMENT_QUICK_START.md` for deployment instructions.

## 📂 Project Structure

```
backend/
├── app/
│   ├── core/          # Security, Config, Dependencies
│   ├── models/         # SQLAlchemy Models (User, Connection, Post, Tag)
│   ├── routers/        # API Endpoints (Auth, Feed, Connections, Posts, Tags)
│   ├── schemas/        # Pydantic Schemas
│   ├── db.py           # Database Session
│   └── main.py         # App Entrypoint
├── migrations/         # Alembic Migrations
├── tests/              # Test Suite
├── seed.py             # Database Seeding Script
├── Dockerfile          # Container Configuration
└── requirements.txt    # Python Dependencies

frontend/
├── src/
│   ├── components/     # React Components
│   ├── context/        # React Context (Auth)
│   ├── pages/          # Page Components
│   └── api.js          # API Client
├── Dockerfile          # Container Configuration
└── nginx.conf          # Nginx Configuration
```

## 📚 Documentation

- `README.md` - This file (project overview)
- `VPS_SETUP_GUIDE.md` - Complete VPS setup and backend deployment guide
- `CLOUDFLARE_PAGES_SETUP.md` - Frontend deployment to Cloudflare Pages
- `DEPLOYMENT_QUICK_START.md` - Quick deployment guide
- `PRODUCTION_DEPLOYMENT_PLAN.md` - Detailed production deployment
- `TECHNICAL_REVIEW_V2.md` - Technical review and improvements
