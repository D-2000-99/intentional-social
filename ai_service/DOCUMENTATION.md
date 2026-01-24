# AI Service Documentation

## Overview

The AI Service is a separate microservice that processes social media posts to generate digest summaries and importance scores using OpenAI's API. It runs as a Docker container and can be executed on-demand to process pending posts from the current week.

## Purpose

The service generates:
- **Digest Summaries**: Third-person, factual observations about posts (e.g., "Sarah enjoyed matcha on a quiet afternoon.")
- **Importance Scores**: Internal scores (0-10) used for Digest filtering and curation

These are stored in the database and used by the Digest feature to create a curated, reflective weekly view of posts.

## Architecture

### Components

```
ai_service/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management (env vars)
│   ├── database.py          # Database connection & session management
│   ├── models.py            # Database models (Post, User)
│   ├── openai_client.py     # OpenAI API integration & image processing
│   ├── s3_helper.py         # S3/R2 presigned URL generation
│   ├── post_processor.py    # Post processing logic
│   ├── week_utils.py        # Week calculation utilities
│   └── main.py              # Entry point & CLI
├── Dockerfile               # Container definition
├── docker-compose.yml       # Service orchestration
├── requirements.txt         # Python dependencies
└── README.md               # Quick start guide
```

### Key Modules

#### `config.py`
- Loads configuration from environment variables
- Manages OpenAI, database, and S3/R2 settings
- Provides defaults for optional settings

#### `database.py`
- Creates SQLAlchemy engine and session factory
- Provides context manager for database sessions
- Handles connection pooling

#### `openai_client.py`
- Downloads and encodes images to base64
- Generates digest summaries using OpenAI Vision API
- Parses JSON responses with fallback handling
- Implements importance scoring guidelines

#### `post_processor.py`
- Prepares post data (author names, photo URLs)
- Processes single posts
- Handles batch processing of multiple posts

#### `week_utils.py`
- Calculates week bounds (Sunday to Saturday)
- Used for filtering posts by current week

#### `main.py`
- CLI entry point
- Supports three modes: single post, batch, continuous
- Handles argument parsing and execution flow

## Functionality

### Processing Modes

#### 1. Batch Mode (Default)
Processes all pending posts from the current week, then exits.

```bash
python -m app.main --batch
```

**Behavior:**
- Finds all posts from current week without `digest_summary`
- Prepares all posts (loads authors, generates presigned URLs)
- Processes each post sequentially with OpenAI API
- Updates database with summaries and importance scores
- Exits when complete

**Use Case:** On-demand processing when you want to update all pending posts.

#### 2. Single Post Mode
Processes a specific post by ID.

```bash
python -m app.main --post-id 123
```

**Use Case:** Testing or reprocessing a specific post.

#### 3. Continuous Mode
Continuously monitors and processes posts one at a time.

```bash
python -m app.main --continuous --interval 5
```

**Use Case:** Long-running service that processes posts as they arrive (not recommended for production due to cost/resource concerns).

### Processing Flow

1. **Query Database**: Find posts from current week without `digest_summary`
2. **Prepare Data**: 
   - Load author information
   - Convert S3 keys to presigned URLs (if S3/R2 configured)
   - Prepare image URLs for OpenAI Vision API
3. **Generate Summary**:
   - Call OpenAI API with post content and images
   - Parse JSON response (summary + importance score)
   - Handle errors with fallback values
4. **Update Database**:
   - Store `digest_summary` (text)
   - Store `importance_score` (float 0-10)
   - Commit transaction

### Importance Scoring

The AI assigns importance scores based on content type:

- **8-10**: Major life events (weddings, births, graduations, family gatherings)
- **6-7**: Meaningful social events (parties, celebrations, significant outings)
- **5-6**: Beautiful photos and scenic content (vistas, landscapes, nature photography)
- **4-5**: Regular activities (meals, casual outings, work updates)
- **2-3**: Routine moments (coffee, desk shots, routine selfies)
- **0-1**: Very routine or minimal content

These scores are used by the Digest router to filter and curate posts (see Digest filtering rules).

### Image Processing

- Downloads images from URLs (presigned or direct)
- Encodes to base64 for OpenAI Vision API
- Supports JPEG, PNG, WebP, GIF
- Enforces size limits (default: 20MB)
- Uses "low" detail level by default (cost optimization)

## Configuration

### Required Environment Variables

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
OPENAI_API_KEY=sk-...
```

### Optional Environment Variables

```env
OPENAI_MODEL_NAME=gpt-4o-mini          # Model to use
LOG_LEVEL=INFO                          # Logging level
MAX_IMAGE_SIZE_MB=20                    # Max image size
IMAGE_DETAIL_LEVEL=low                  # Image detail (low/high/auto)

# S3/R2 Configuration (for presigned URLs)
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ENDPOINT_URL=https://...
R2_BUCKET_NAME=...
R2_REGION=auto
STORAGE_PRESIGNED_URL_EXPIRATION=3600
```

## Usage

### Docker Compose (Recommended)

```bash
cd ai_service
cp .env.example .env
# Edit .env: MAIN_BACKEND_NETWORK (main app's Docker network), DATABASE_URL, OPENAI_API_KEY
# Ensure main backend docker-compose is running first (creates the network)
docker-compose up
```

This will:
1. Build the container
2. Join the main backend's Docker network (external; set `MAIN_BACKEND_NETWORK` in `.env`)
3. Process all pending posts from current week
4. Exit when complete

The service connects to the main backend's database network. Set `MAIN_BACKEND_NETWORK` in `.env` to your main app's Docker network (e.g. `myapp_default`, `social_100_default`). Use `docker network ls` to see the actual name.

### Standalone Docker

```bash
# Build
docker build -t ai-service ./ai_service

# Run batch mode
docker run --env-file .env ai-service

# Run single post
docker run --env-file .env ai-service python -m app.main --post-id 123 --no-continuous
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=...
export OPENAI_API_KEY=...

# Run
python -m app.main --batch
```

## Database Schema

The service updates the `posts` table with:

- `digest_summary` (TEXT, nullable): AI-generated third-person summary
- `importance_score` (FLOAT, nullable): Internal importance score (0-10)

Posts are identified as "pending" when `digest_summary IS NULL`.

## Error Handling

- **Missing Posts**: Logs warning and skips
- **Missing Authors**: Uses "Unknown" as fallback
- **Image Download Failures**: Continues without image
- **OpenAI API Errors**: Returns fallback summary ("{author} shared a moment.") with default importance (5.0)
- **JSON Parse Errors**: Attempts to extract JSON from response, falls back to defaults
- **Database Errors**: Rolls back transaction, logs error, continues with next post

## Integration with Main Backend

- **Shared Database**: Reads from and writes to the same PostgreSQL database
- **No API Communication**: Direct database access (no HTTP endpoints)
- **Independent Deployment**: Can be run separately from main backend
- **On-Demand Execution**: Typically run manually or via scheduled job

## Cost Considerations

- **Per-Post Processing**: Each post = 1 OpenAI API call
- **Image Processing**: Vision API calls cost more than text-only
- **Batch Processing**: More efficient than continuous polling
- **Model Selection**: `gpt-4o-mini` is cost-effective for this use case

## Future Enhancements

Potential improvements:
- True OpenAI Batch API integration (50% cost reduction, async processing)
- Parallel processing of multiple posts
- Retry logic with exponential backoff
- Rate limiting protection
- Metrics and monitoring
- Scheduled processing (cron integration)

## Troubleshooting

### Service exits immediately
- Check database connection (`DATABASE_URL`; use hostname `db` when using Docker)
- Verify OpenAI API key is valid
- Check logs for error messages

### Network / Docker Compose issues
- Ensure main backend docker-compose is running first (it creates the network)
- Set `MAIN_BACKEND_NETWORK` in `.env` to your main app's Docker network (typically `{project_dir}_default`)
- Run `docker network ls` to see available networks

### Posts not being processed
- Verify posts exist in current week (Sunday-Saturday)
- Check if posts already have `digest_summary` (already processed)
- Review database query logs

### Image processing fails
- Verify S3/R2 credentials if using S3 keys
- Check image URLs are accessible
- Review image size limits

### OpenAI API errors
- Verify API key has sufficient credits
- Check rate limits
- Review model name is correct
- Check network connectivity

## Logging

Logs are output to stdout with format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

Set via `LOG_LEVEL` environment variable (default: INFO).

