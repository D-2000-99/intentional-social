# Docker Setup for Observability

## Overview

The observability system can be run in Docker with three different configurations:

1. **Standalone** (`docker-compose.yml` or `docker-compose.standalone.yml`) - Includes its own database
2. **Shared Database** (`docker-compose.shared-db.yml`) - Connects to the main backend's database network

## Quick Start

### Production

```bash
# First, ensure main backend production is running
cd ..  # Go to project root
docker-compose up -d

# Then start observability for production
cd observability
cp .env.example .env
# Edit .env:
#   - MAIN_BACKEND_NETWORK: main backend's Docker network (e.g. myapp_default)
#   - DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social
docker-compose -f docker-compose.prod.yml up -d --build
```

### Development

```bash
# First, ensure main backend development is running
cd ..  # Go to project root
docker-compose -f docker-compose-dev.yml up -d

# Then start observability for development
cd observability
cp .env.example .env
# Edit .env:
#   - MAIN_BACKEND_NETWORK: main backend's Docker network (e.g. myapp_default)
#   - DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social_dev
docker-compose -f docker-compose.dev.yml up -d --build
```

## Docker Compose Files

- `docker-compose.prod.yml` - For production (connects to prod database)
- `docker-compose.dev.yml` - For development (connects to dev database)

Both files connect to the main backend's Docker network (external, pre-existing) and create an **observability** network for observability services.

- **MAIN_BACKEND_NETWORK** (in `.env`): The main backend's Docker network (typically `{project_dir}_default`, e.g. `social_100_default` or `myapp_default`). Must exist; created by the main app's compose.
- **observability-network**: Created by these compose files (`driver: bridge`). No config needed.

The key difference between prod and dev is the `DATABASE_URL` pointing to different database names.

## Build Context

The Dockerfile uses the project root as the build context to include both:
- Main backend code (for imports)
- Observability backend code

The structure in the container is:
```
/app
├── backend/          # Main backend (for imports)
└── observability/    # Observability backend
    └── app/          # Application code
```

## Environment Variables

Key environment variables needed in `.env` (see `.env.example` for a full template):

**Docker network (required for compose, external/main backend only):**
```env
MAIN_BACKEND_NETWORK=social_100_default   # or your app's network, e.g. myapp_default
```

**For Production (`docker-compose.prod.yml`):**
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social
```

**For Development (`docker-compose.dev.yml`):**
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social_dev
```

**Security & app config:**
```env
SECRET_KEY=your-secret-key
MODERATOR_EMAILS=moderator1@example.com,moderator2@example.com
OBSERVABILITY_CORS_ORIGINS=http://localhost:5175
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8002/auth/google/callback
# AWS/R2 (same as main backend, for user deletion)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
```

## Ports

- **Observability Backend**: `8002` (exposed from container port 8001)
  - Avoids conflicts with prod backend on 8000 and dev backend on 8001
- **Observability Frontend**: Not in Docker - deployed on Cloudflare Pages (see CLOUDFLARE_DEPLOYMENT.md)
- **Database**: Uses shared database from main backend (no separate database service)

## Frontend Deployment

The frontend is **not** included in Docker Compose as it's deployed separately on Cloudflare Pages.

To build for Cloudflare Pages:
```bash
cd observability/frontend
npm install  # Install dependencies first (required!)
npm run build
```

For local development:
```bash
cd observability/frontend
npm install  # Install dependencies first (required!)
npm run dev  # Runs on http://localhost:5174
```

The output will be in `frontend/dist/` which should be deployed to Cloudflare Pages.

## Database Migrations

The observability backend uses the same database schema as the main backend. Migrations should be run from the main backend:

**Production:**
```bash
# From project root
docker-compose exec backend alembic upgrade head
```

**Development:**
```bash
# From project root
docker-compose -f docker-compose-dev.yml exec backend alembic upgrade head
```

## Troubleshooting

### Import Errors

If you see import errors related to the main backend, ensure:
1. The build context includes the main backend directory
2. The Dockerfile copies both backend directories correctly
3. The path calculations in the code match the container structure

### Database Connection Issues

1. Ensure the appropriate main backend docker-compose is running:
   - Production: `docker-compose up -d` (from project root)
   - Development: `docker-compose -f docker-compose-dev.yml up -d` (from project root)
2. Set `MAIN_BACKEND_NETWORK` in `.env` to your main backend's network (e.g. `myapp_default`; Docker uses `{project_dir}_default`).
3. Verify DATABASE_URL uses:
   - Correct hostname: `db` (for docker network)
   - Correct database name: `intentional_social` (prod) or `intentional_social_dev` (dev)

### Network Issues

Only the **main backend** network is external. Ensure:

- **MAIN_BACKEND_NETWORK** in `.env` matches the main backend's Docker network. Use `docker network ls` to see the actual name (typically `{project_dir}_default`).
- The **observability** network is created automatically by the compose file; no setup needed.

