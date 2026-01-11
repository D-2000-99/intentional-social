# Moderator Dashboard (Observability)

Separate backend and frontend application for content moderation and user management.

## Setup

### Docker Compose (Recommended)

1. Navigate to the observability directory:
   ```bash
   cd observability
   ```

2. Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Choose the appropriate compose file:
   
   **For Production:**
   ```bash
   # Ensure main backend docker-compose.yml is running first
   docker-compose -f docker-compose.prod.yml up -d --build
   ```
   - Set `DATABASE_URL` in `.env` to: `postgresql://postgres:postgres@db:5432/intentional_social`
   - Connects to production database network

   **For Development:**
   ```bash
   # Ensure main backend docker-compose-dev.yml is running first
   docker-compose -f docker-compose.dev.yml up -d --build
   ```
   - Set `DATABASE_URL` in `.env` to: `postgresql://postgres:postgres@db:5432/intentional_social_dev`
   - Connects to development database network

6. Access the dashboard at `http://localhost:5175`

### Manual Setup

#### Backend

1. Navigate to the observability backend directory:
   ```bash
   cd observability/backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Ensure the main backend's database migration has been run (to create `is_banned` column and `reported_posts` table).

4. Set up environment variables in `.env` (see `.env.example` for reference):
   - `DATABASE_URL`: Connection string to the same database as main backend
   - `SECRET_KEY`: Same as main backend
   - `MODERATOR_EMAILS`: Comma-separated list of moderator email addresses
   - `OBSERVABILITY_CORS_ORIGINS`: CORS allowed origins
   - Google OAuth credentials (same as main backend)
   - AWS S3 credentials (same as main backend, for user deletion)

5. Run the backend:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
   # Note: In Docker, this is exposed on port 8002 to avoid conflict with dev backend
   ```

#### Frontend

1. Navigate to the observability frontend directory:
   ```bash
   cd observability/frontend
   ```

2. Install dependencies (required before running dev):
   ```bash
   npm install
   ```

3. Set up environment variables (optional, defaults to localhost:8002):
   ```
   VITE_OBSERVABILITY_API_URL=http://localhost:8002
   ```

4. Run the frontend:
   ```bash
   npm run dev
   ```

5. For local development: `npm run dev` (runs on `http://localhost:5174`)
6. For production: Deploy to Cloudflare Pages (see CLOUDFLARE_DEPLOYMENT.md)

## Features

- **Reported Posts**: View and manage reported posts from the main application
- **User Management**: 
  - List all users with search functionality
  - Ban/Unban users
  - Delete users (with proper cascade deletion of all associated data and S3 images)
- **Authentication**: Google OAuth restricted to emails in `MODERATOR_EMAILS` environment variable

## Security

- Only users with emails listed in `MODERATOR_EMAILS` can access the dashboard
- All endpoints require moderator authentication
- Banned users cannot access the main application
- User deletion properly cascades through all related tables and deletes S3 images

## Docker Compose Files

- `docker-compose.yml`: Default compose file with included database service
- `docker-compose.standalone.yml`: Standalone version (same as default)
- `docker-compose.shared-db.yml`: Connects to main backend's database network (requires main backend to be running)

To use the shared database version:
```bash
# Make sure main backend docker-compose is running first
cd ..  # Go to project root
docker-compose up -d  # Start main backend and database

# Then start observability with shared database
cd observability
docker-compose -f docker-compose.shared-db.yml up -d --build
```

## Ports

- Observability Backend: `8002` (Docker) or `8001` (manual)
- Observability Frontend: `5174` (local dev via npm) or Cloudflare Pages (production)
- Database (if included): `5434`
