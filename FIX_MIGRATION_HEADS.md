# Fix Multiple Migration Heads Issue

## Problem

Alembic detected multiple head revisions, causing the container to restart continuously:
```
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head'
```

## Root Cause

Two migration branches exist from `cd8dc5e61fed`:
1. `cd8dc5e61fed` → `add_email_verification` → `f8a9b2c3d4e5` (add_photo_urls_to_posts)
2. `cd8dc5e61fed` → `a1b2c3d4e5f6` (fix_connection_status_enum_case)

This creates two "heads" that need to be merged.

## Solution

A merge migration has been created: `merge_enum_fix_and_photo_urls.py`

This migration merges both branches into a single head.

## Steps to Fix

### Option 1: Apply Merge Migration (Recommended)

1. **Copy the merge migration to your VPS:**
   ```bash
   # The file is already in your repo, just pull it
   cd ~/intentional-social
   git pull  # or copy the file manually
   ```

2. **Check current migration status:**
   ```bash
   docker compose exec backend alembic heads
   ```
   This should show both heads: `f8a9b2c3d4e5` and `a1b2c3d4e5f6`

3. **Apply the merge migration:**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

4. **Verify there's only one head now:**
   ```bash
   docker compose exec backend alembic heads
   ```
   Should show: `merge_heads_001`

5. **Restart the backend:**
   ```bash
   docker compose restart backend
   ```

### Option 2: Manual Fix (If merge doesn't work)

If the merge migration doesn't work, you can manually fix the migration chain:

1. **Check which migrations are applied:**
   ```bash
   docker compose exec backend alembic current
   ```

2. **Check the migration history:**
   ```bash
   docker compose exec backend alembic history
   ```

3. **If one branch hasn't been applied, apply it first:**
   ```bash
   # Apply the enum fix branch
   docker compose exec backend alembic upgrade a1b2c3d4e5f6
   
   # Or apply the photo_urls branch
   docker compose exec backend alembic upgrade f8a9b2c3d4e5
   ```

4. **Then apply the merge:**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

### Option 3: Reset and Reapply (Nuclear Option)

⚠️ **WARNING: This will lose data if you don't have backups!**

If you're in development and can afford to reset:

1. **Backup your database first:**
   ```bash
   docker compose exec db pg_dump -U postgres intentional_social > backup_$(date +%Y%m%d).sql
   ```

2. **Drop and recreate the database:**
   ```bash
   docker compose down -v  # This removes volumes!
   docker compose up -d db
   ```

3. **Run all migrations from scratch:**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

## Verification

After fixing, verify:

1. **Container starts successfully:**
   ```bash
   docker compose logs backend | tail -20
   ```
   Should see: "Application startup complete" without migration errors

2. **Only one head exists:**
   ```bash
   docker compose exec backend alembic heads
   ```

3. **Health check passes:**
   ```bash
   curl http://localhost:8000/health
   ```

## Migration Chain (After Fix)

```
0bc1c6bf2c9 (create_users_follows_posts_tables)
  ↓
cefd6d801857 (add_follow_indexes)
  ↓
0554a209c7a0 (initial_migration)
  ↓
ae8fcb7881c7 (replace_follows_with_connections)
  ↓
e734d765d3ad (add_tag_system_tables)
  ↓
cd8dc5e61fed (convert_connection_status_to_enum)
  ↓
├─→ add_email_verification
│     ↓
│   f8a9b2c3d4e5 (add_photo_urls_to_posts)
│
└─→ a1b2c3d4e5f6 (fix_connection_status_enum_case)
      ↓
    merge_heads_001 (MERGE) ← Single head
```

## Troubleshooting

### Error: "Can't locate revision identified by..."

This means the database is in an inconsistent state. Check:
```bash
docker compose exec backend alembic current
docker compose exec backend alembic heads
docker compose exec backend alembic history
```

### Error: "Target database is not up to date"

You may need to stamp the database:
```bash
# Check what's actually in the database
docker compose exec db psql -U postgres intentional_social -c "SELECT version_num FROM alembic_version;"

# If needed, stamp to a specific revision
docker compose exec backend alembic stamp <revision_id>
```

### Still Having Issues?

1. Check migration files are in the correct directory
2. Verify file permissions
3. Check for syntax errors in migration files
4. Review alembic.ini configuration
