# Port Mapping Reference

This document explains the port assignments to avoid conflicts with the main application.

## Docker Compose Files

- `docker-compose.prod.yml` - Production (connects to prod database)
- `docker-compose.dev.yml` - Development (connects to dev database)

## Main Application Ports

### Production (`docker-compose.yml`)
- Backend: `8000`
- Database: `5432`

### Development (`docker-compose-dev.yml`)
- Backend: `8001` ⚠️
- Database: `5433` ⚠️

## Observability Ports

To avoid conflicts with the development environment, observability uses different ports:

- **Observability Backend**: `8002` (avoids conflict with prod backend on 8000 and dev backend on 8001)
- **Observability Frontend**: `5174` (local dev) or Cloudflare Pages (production)
- **Observability Database**: Uses shared database from main backend (no separate database service)

## Summary

| Service | Production | Development | Observability |
|---------|-----------|-------------|---------------|
| Main Backend | 8000 | 8001 | - |
| Observability Backend | - | - | 8002 |
| Main Database | 5432 | 5433 | - |
| Observability Database | Shared (prod) | Shared (dev) | Uses main backend DB |
| Main Frontend | 80/443 | 5173 | - |
| Observability Frontend | Cloudflare Pages | 5174 (local dev) | Not in Docker |

## Network Configuration

When using `docker-compose.prod.yml` or `docker-compose.dev.yml`, the observability backend connects to the main backend's network (`social_100_default`) to access the shared database. The database service name in the network is `db`, so the DATABASE_URL should use `db` as the hostname:

**For Production (`docker-compose.prod.yml`):**
```
DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social
```

**For Development (`docker-compose.dev.yml`):**
```
DATABASE_URL=postgresql://postgres:postgres@db:5432/intentional_social_dev
```

