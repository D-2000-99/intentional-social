---
description: Apply backend optimizations from backend_analysis.md
---

# Backend Optimization Implementation Plan

This workflow applies all recommended fixes from backend_analysis.md except Connection Pool Tuning.

## Phase 1: Database Indexes (Critical - 1 hour)

1. Create Alembic migration for performance indexes
2. Add indexes for:
   - Composite index on connections (user_a_id, user_b_id, status)
   - Index on post.created_at (DESC)
   - Index on post.author_id
   - Composite index on post_audience_tags (post_id, tag_id)
   - Composite index on user_tags (owner_user_id, target_user_id, tag_id)
   - Index on comments.post_id
   - Index on comments.author_id
3. Run migration

## Phase 2: Extract Shared Services (Critical - 6 hours)

1. Create `app/services/` directory
2. Create `app/services/__init__.py`
3. Create `app/services/post_service.py` with:
   - `filter_posts_by_audience()` method
   - `batch_load_audience_tags()` method
4. Create `app/services/connection_service.py` with:
   - `get_connected_user_ids()` method
   - `are_connected()` method
5. Create `app/services/storage_service.py` with:
   - `get_presigned_url()` method (with caching support)
   - `batch_get_presigned_urls()` method

## Phase 3: Fix N+1 Query Problems (Critical - 4 hours)

1. Update `feed.py` to use `ConnectionService.get_connected_user_ids()`
2. Update `feed.py` to use `PostService.batch_load_audience_tags()`
3. Update `digest.py` to use `ConnectionService.get_connected_user_ids()`
4. Update `digest.py` to use `PostService.batch_load_audience_tags()`
5. Update `posts.py` to use `PostService.batch_load_audience_tags()`

## Phase 4: Standardize Error Handling (High Priority - 4 hours)

1. Create `app/core/exceptions.py` with custom exception classes
2. Add global exception handlers to `main.py`
3. Update routers to use custom exceptions

## Phase 5: Improve Transaction Management (High Priority - 2 hours)

1. Create `app/core/db_utils.py` with transaction context manager
2. Update critical endpoints to use transaction context manager

## Phase 6: Add Security Improvements (Medium Priority - 4 hours)

1. Add request size limit middleware
2. Add rate limiting to more endpoints
3. Add input sanitization for user content

## Phase 7: Add Monitoring (Medium Priority - 2 hours)

1. Add database health check endpoint
2. Add custom Prometheus metrics
3. Add structured logging

## Phase 8: Caching Layer (Optional - requires Redis setup)

1. Add Redis configuration to config.py
2. Create `app/core/cache.py`
3. Update routers to use caching

Total Estimated Time (excluding caching): ~23 hours
