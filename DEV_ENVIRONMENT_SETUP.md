# Dev Environment Setup Guide

## Overview

This guide covers setting up a separate development environment that runs alongside production. The dev environment uses:
- Backend on port **8001** (prod uses 8000)
- Separate database: `intentional_social_dev` (prod uses `intentional_social`)
- Separate Docker volume: `postgres_data_dev`
- API endpoint: `https://api-dev.intentionalsocial.org` (prod uses `https://api.intentionalsocial.org`)

## Prerequisites

- Nginx configured (already done - routes `api-dev.intentionalsocial.org` to port 8001)
- SSL certificates configured for `api-dev.intentionalsocial.org`
- Cloudflare Pages preview deployments configured with `VITE_API_URL=https://api-dev.intentionalsocial.org`

## Backend Setup

### 1. Create Dev Docker Compose File

The `docker-compose-dev.yml` file is already created with:
- Backend service on port `8001:8000`
- Database service on port `5433:5432` (to avoid conflict with prod on 5432)
- Database name: `intentional_social_dev`
- Separate volume: `postgres_data_dev`

### 2. Configure Backend `.env` File

In your dev cloned folder, create/update `backend/.env`:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social_dev

# CORS Configuration - Include Cloudflare Pages preview URLs
# Format: https://<branch-name>--<project-name>.pages.dev
# Example: https://dev--intentional-social.pages.dev
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://api-dev.intentionalsocial.org,https://intentional-social.pages.dev,https://<your-branch>--intentional-social.pages.dev

# Frontend URL for OAuth redirects
FRONTEND_URL=https://<your-branch>--intentional-social.pages.dev

# Google OAuth Configuration
GOOGLE_REDIRECT_URI=https://api-dev.intentionalsocial.org/auth/google/callback

# Other settings (copy from prod or use dev values)
SECRET_KEY=your-dev-secret-key-here-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_CONNECTIONS=10

# S3 Configuration (can use same as prod or separate dev bucket)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket
S3_PHOTO_PREFIX=posts/photos
S3_AVATAR_PREFIX=users/avatars
S3_PRESIGNED_URL_EXPIRATION=3600

# Google OAuth (same Client ID/Secret, but different redirect URI)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 3. Google OAuth Configuration

**Important**: Add the dev redirect URI in Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services → Credentials
3. Edit your OAuth 2.0 Client ID
4. Add to "Authorized redirect URIs":
   - `https://api-dev.intentionalsocial.org/auth/google/callback` (dev)
   - Keep existing: `https://api.intentionalsocial.org/auth/google/callback` (prod)

### 4. Start Dev Environment

```bash
# Navigate to your dev cloned folder
cd ~/intentional-social-dev  # or wherever your dev folder is

# Start dev containers
docker compose -f docker-compose-dev.yml up -d

# Check logs
docker compose -f docker-compose-dev.yml logs -f backend

# Verify backend is running
curl https://api-dev.intentionalsocial.org/health
```

### 5. Initialize Dev Database

```bash
# Run migrations in dev environment
docker compose -f docker-compose-dev.yml exec backend alembic upgrade head

# Verify database
docker compose -f docker-compose-dev.yml exec db psql -U postgres -d intentional_social_dev -c "\dt"
```

## Port Configuration Summary

| Service | Dev Port | Prod Port | Notes |
|---------|----------|-----------|-------|
| Backend API | 8001 | 8000 | Nginx routes api-dev → 8001, api → 8000 |
| Database | 5433 | 5432 | Different ports to avoid conflicts |

## Database Management

### Dev Database Commands

```bash
# Connect to dev database
docker compose -f docker-compose-dev.yml exec db psql -U postgres -d intentional_social_dev

# Backup dev database
docker compose -f docker-compose-dev.yml exec db pg_dump -U postgres intentional_social_dev > dev_backup_$(date +%Y%m%d).sql

# Restore dev database
docker compose -f docker-compose-dev.yml exec -T db psql -U postgres intentional_social_dev < dev_backup.sql
```

### Migration Workflow

1. **Create migration in dev**:
   ```bash
   docker compose -f docker-compose-dev.yml exec backend alembic revision --autogenerate -m "description"
   ```

2. **Test migration in dev**:
   ```bash
   docker compose -f docker-compose-dev.yml exec backend alembic upgrade head
   ```

3. **After merge to master, apply to prod**:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

## CORS Configuration Notes

Cloudflare Pages preview URLs follow this pattern:
- Format: `https://<branch-name>--<project-name>.pages.dev`
- Example: `https://dev--intentional-social.pages.dev`
- Note: Branch names with hyphens become double hyphens in the URL

**Important**: Update `CORS_ORIGINS` in dev `.env` to include your preview branch URL(s).

## Troubleshooting

### Backend not accessible

```bash
# Check if containers are running
docker compose -f docker-compose-dev.yml ps

# Check backend logs
docker compose -f docker-compose-dev.yml logs backend

# Verify port 8001 is accessible locally
curl http://localhost:8001/health
```

### CORS errors

1. Verify `CORS_ORIGINS` in dev `.env` includes your Cloudflare Pages preview URL
2. Restart backend: `docker compose -f docker-compose-dev.yml restart backend`
3. Check backend logs for CORS-related errors

### Database connection issues

```bash
# Check database is running
docker compose -f docker-compose-dev.yml ps db

# Check database logs
docker compose -f docker-compose-dev.yml logs db

# Verify DATABASE_URL in .env matches docker-compose-dev.yml
```

### Port conflicts

If port 8001 or 5433 are already in use:
- Check: `sudo lsof -i :8001` or `sudo lsof -i :5433`
- Stop conflicting services or change ports in `docker-compose-dev.yml`

## Quick Reference

### Start Dev Environment
```bash
docker compose -f docker-compose-dev.yml up -d
```

### Stop Dev Environment
```bash
docker compose -f docker-compose-dev.yml down
```

### View Logs
```bash
docker compose -f docker-compose-dev.yml logs -f backend
```

### Run Migrations (Dev)
```bash
docker compose -f docker-compose-dev.yml exec backend alembic upgrade head
```

### Check Health
```bash
curl https://api-dev.intentionalsocial.org/health
```
