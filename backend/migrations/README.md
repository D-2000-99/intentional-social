# Notifications Table Migration

This migration creates the `notifications` table required for the notification bell feature.

## ⚠️ IMPORTANT: If Backend is Restarting

If your backend container is in a restart loop, run the migration directly on the database container:

### Option 1: Run SQL directly via psql (RECOMMENDED when backend is down)

```bash
# From project root - pipe SQL file directly
docker-compose exec -T db psql -U postgres -d intentional_social < backend/migrations/create_notifications_table.sql
```

### Option 2: Interactive psql session

```bash
# Connect to the database container
docker-compose exec db psql -U postgres -d intentional_social

# Then paste and run the SQL commands from create_notifications_table.sql
# Or copy the file into the container first:
docker cp backend/migrations/create_notifications_table.sql social_100-db-1:/tmp/migration.sql
docker-compose exec db psql -U postgres -d intentional_social -f /tmp/migration.sql
```

### Option 3: Run via Docker backend (when backend is working)

```bash
# From the project root
docker-compose exec backend python migrations/run_migration.py
```

Or if using docker-compose-dev.yml:
```bash
docker-compose -f docker-compose-dev.yml exec backend python migrations/run_migration.py
```

## Option 3: Run Python script locally

If you have the database connection configured locally:

```bash
cd backend
python migrations/run_migration.py
```

## Verification

After running the migration, verify the table was created:

```bash
docker-compose exec db psql -U postgres -d intentional_social -c "\d notifications"
```

You should see the notifications table with all columns and indexes.
