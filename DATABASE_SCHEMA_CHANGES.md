# Database Schema Changes Tracking

## Purpose

This document tracks all database schema changes to ensure proper review and testing before applying to production. **Always update this document when creating new migrations.**

## Review Process

1. **Create migration in dev**: Test thoroughly in dev environment
2. **Document change here**: Add entry to this file with migration details
3. **Review**: Team reviews the change and impact
4. **Apply to prod**: After merge to master, apply migration to production

---

## Schema Change Log

### Template for New Entries

```markdown
### [Migration ID] - [Brief Description]
- **Date**: YYYY-MM-DD
- **Author**: Your Name
- **Migration File**: `versions/xxxxx_description.py`
- **Type**: [CREATE TABLE | ALTER TABLE | DROP TABLE | ADD COLUMN | MODIFY COLUMN | etc.]
- **Description**: Detailed description of the change
- **Tables Affected**: List of tables modified
- **Breaking Changes**: Yes/No - If yes, describe impact
- **Rollback Plan**: How to rollback if needed
- **Tested in Dev**: Yes/No
- **Applied to Prod**: Yes/No - Date if yes
- **Notes**: Any additional notes or considerations
```

---

## Current Migrations

### merge_enum_fix_and_photo_urls - Merge Migration
- **Date**: [Previous]
- **Type**: MERGE
- **Description**: Merged two migration branches (enum fix and photo URLs)
- **Status**: Applied to prod

### add_photo_urls_to_posts - Add Photo URLs Support
- **Date**: [Previous]
- **Type**: ADD COLUMN
- **Description**: Added `photo_urls` JSONB column to posts table
- **Tables Affected**: `posts`
- **Breaking Changes**: No
- **Status**: Applied to prod

### fix_connection_status_enum_case - Fix Connection Status Enum
- **Date**: [Previous]
- **Type**: ALTER COLUMN
- **Description**: Fixed enum case sensitivity for connection status
- **Tables Affected**: `connections`
- **Breaking Changes**: No
- **Status**: Applied to prod

### e734d765d3ad - Add Tag System Tables
- **Date**: [Previous]
- **Type**: CREATE TABLE
- **Description**: Added tag system with tags, connection_tags, and post_audience_tags tables
- **Tables Affected**: `tags`, `connection_tags`, `post_audience_tags`
- **Breaking Changes**: No
- **Status**: Applied to prod

### ae8fcb7881c7 - Replace Follows with Connections
- **Date**: [Previous]
- **Type**: DROP TABLE, CREATE TABLE
- **Description**: Replaced follows table with connections table
- **Tables Affected**: `follows` (dropped), `connections` (created)
- **Breaking Changes**: Yes - Data migration required
- **Status**: Applied to prod

---

## Pending Migrations (Not Yet Applied to Prod)

_Add new migrations here before applying to production_

---

## Migration Checklist

Before applying a migration to production:

- [ ] Migration created and tested in dev environment
- [ ] Migration documented in this file
- [ ] Code review completed
- [ ] Breaking changes identified and documented
- [ ] Rollback plan documented
- [ ] Database backup created (for prod)
- [ ] Migration tested on production-like data (if possible)
- [ ] Team notified of schema change
- [ ] Applied to production
- [ ] Verified in production
- [ ] Updated status in this document

## Rollback Procedures

### If Migration Fails in Production

1. **Stop the application** (if migration is blocking)
2. **Check migration status**: `docker compose exec backend alembic current`
3. **Rollback if needed**: `docker compose exec backend alembic downgrade -1`
4. **Restore from backup** if data corruption occurred
5. **Document the issue** in this file
6. **Fix the migration** and retest in dev

### Creating a Rollback Migration

If you need to rollback a change:

```bash
# Create a new migration to undo the change
docker compose -f docker-compose-dev.yml exec backend alembic revision -m "rollback_description"
```

Then manually edit the migration file to reverse the changes.

## Best Practices

1. **Always test in dev first**: Never create migrations directly in production
2. **Document thoroughly**: Include clear descriptions of what changed and why
3. **Consider breaking changes**: Think about how the change affects existing code
4. **Backup before prod**: Always backup production database before migrations
5. **Review with team**: Get code review before applying to production
6. **Monitor after deployment**: Watch logs and metrics after applying to prod

## Migration Commands Reference

### Dev Environment
```bash
# Create new migration
docker compose -f docker-compose-dev.yml exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker compose -f docker-compose-dev.yml exec backend alembic upgrade head

# Check current version
docker compose -f docker-compose-dev.yml exec backend alembic current

# View migration history
docker compose -f docker-compose-dev.yml exec backend alembic history

# Rollback one version
docker compose -f docker-compose-dev.yml exec backend alembic downgrade -1
```

### Production Environment
```bash
# Apply migrations (after merge to master)
docker compose exec backend alembic upgrade head

# Check current version
docker compose exec backend alembic current

# View migration history
docker compose exec backend alembic history
```

---

**Last Updated**: [Update this date when adding new entries]
