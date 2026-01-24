# AI Service for Digest Generation

Separate microservice for generating digest summaries using OpenAI.

**📖 For detailed documentation, see [DOCUMENTATION.md](./DOCUMENTATION.md)**

## Overview

This service processes posts from the database and generates AI-powered summaries for the Digest feature. It runs as a separate Docker container and can be invoked per-post or in batch mode.

## Features

- **Batch processing**: Processes all pending posts from current week, then exits (default behavior)
- Uses OpenAI Vision API to analyze images in posts
- Generates third-person, factual summaries
- Calculates internal importance scores (0-10)
- Updates database with generated summaries
- Per-post LLM calls (sequential processing)

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your values
```

**Docker Compose (main backend network):**
- `MAIN_BACKEND_NETWORK`: Main backend's Docker network (e.g. `myapp_default`, `social_100_default`). Required when using docker-compose.

**Required:**
- `DATABASE_URL`: PostgreSQL connection string (shared with main backend; use hostname `db` when using Docker)
- `OPENAI_API_KEY`: Your OpenAI API key

**Optional:**
- `OPENAI_MODEL_NAME`: Model to use (default: `gpt-4o-mini`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `MAX_IMAGE_SIZE_MB`: Maximum image size to process (default: 20MB)
- `IMAGE_DETAIL_LEVEL`: Image detail level for OpenAI (`low`, `high`, or `auto`)

**S3/R2 Configuration (for generating presigned URLs from S3 keys):**
- `R2_ACCESS_KEY_ID`: R2 access key ID (optional)
- `R2_SECRET_ACCESS_KEY`: R2 secret access key (optional)
- `R2_ENDPOINT_URL`: R2 endpoint URL (optional)
- `R2_BUCKET_NAME`: R2 bucket name (optional)
- `R2_REGION`: R2 region (default: `auto`)
- `STORAGE_PRESIGNED_URL_EXPIRATION`: Presigned URL expiration in seconds (default: 3600)

Note: If S3/R2 credentials are not provided, the service will skip image processing for posts with S3 keys (only direct URLs will work).

## Usage

### Batch mode (default - processes all pending posts, then exits):
```bash
python -m app.main --batch
# or simply (batch is default):
python -m app.main
```

The service will find all unprocessed posts from the current week, process them sequentially, update the database, and exit.

### Process with limit:
```bash
python -m app.main --batch --limit 10
```

### Process a single post:
```bash
python -m app.main --post-id 123 --no-continuous
```

### Continuous mode (for long-running service):
```bash
python -m app.main --continuous --interval 5
```

## Docker

### Build:
```bash
docker build -t ai-service .
```

### Run with Docker Compose (recommended):
```bash
cd ai_service
cp .env.example .env   # if not done yet; set MAIN_BACKEND_NETWORK, DATABASE_URL, OPENAI_API_KEY
# Ensure main backend docker-compose is running first (creates the network)
docker-compose up
```

This will process all pending posts from the current week and exit when complete. The service joins the main backend's Docker network to access the shared database.

### Run standalone (batch mode - default):
```bash
docker run --env-file .env ai-service
```

### Run standalone (single post):
```bash
docker run --env-file .env ai-service python -m app.main --post-id 123 --no-continuous
```

### Run standalone (continuous mode):
```bash
docker run --env-file .env ai-service python -m app.main --continuous
```

## Integration

The service runs on-demand to process pending posts. When started:
- Finds all posts from current week without `digest_summary`
- Processes each post sequentially with OpenAI API
- Updates database with summaries and importance scores
- Exits when complete

The service reads from and writes to the same database as the main backend, so no API communication is needed.

