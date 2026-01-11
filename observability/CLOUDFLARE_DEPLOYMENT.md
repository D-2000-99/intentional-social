# Cloudflare Pages Deployment for Observability Frontend

The observability frontend is deployed on Cloudflare Pages, not via Docker.

## Build Configuration

### Build Command
```bash
cd observability/frontend && npm install && npm run build
```

**Note:** Always run `npm install` first to install dependencies (including vite). The `npm run dev` command requires vite to be installed.

### Output Directory
```
frontend/dist
```

### Environment Variables

Set these in Cloudflare Pages environment variables:

- `VITE_OBSERVABILITY_API_URL` - URL of the observability backend API
  - Example: `https://observability-api.yourdomain.com` or `http://localhost:8002` for local testing

## Build Settings in Cloudflare Pages

1. **Framework preset**: Vite
2. **Build command**: `cd frontend && npm install && npm run build`
3. **Build output directory**: `frontend/dist`
4. **Root directory**: (leave empty or set to repository root)

## Environment Variables

Configure these in Cloudflare Pages dashboard:

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_OBSERVABILITY_API_URL` | Backend API URL | `https://api.yourdomain.com` |

## CORS Configuration

Ensure your observability backend has CORS configured to allow requests from your Cloudflare Pages domain:

```
OBSERVABILITY_CORS_ORIGINS=https://your-cloudflare-pages-domain.pages.dev,https://your-custom-domain.com
```

## Development

For local development, you can still run the frontend with:

```bash
cd observability/frontend
npm install
npm run dev
```

This will run on `http://localhost:5174` by default (configured in `vite.config.js`).

## Production Backend

The observability backend should be deployed separately (via Docker or other means) and accessible at the URL specified in `VITE_OBSERVABILITY_API_URL`.

