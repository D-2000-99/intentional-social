#!/bin/bash

# Backup script for Intentional Social database
# Usage: ./backup.sh

set -e  # Exit on error

# Configuration
BACKUP_DIR="/home/deploy/backups"
APP_DIR="/home/deploy/apps/Social_100"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"
COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}Starting database backup...${NC}"

# Backup database
cd "$APP_DIR"
docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U postgres intentional_social > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database backup created: $BACKUP_FILE${NC}"
    
    # Compress backup
    gzip "$BACKUP_FILE"
    echo -e "${GREEN}✓ Backup compressed: $BACKUP_FILE.gz${NC}"
    
    # Calculate backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
    echo -e "${GREEN}✓ Backup size: $BACKUP_SIZE${NC}"
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete
    echo -e "${GREEN}✓ Old backups cleaned (keeping last 7 days)${NC}"
    
    # Count total backups
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ Total backups: $BACKUP_COUNT${NC}"
    
    echo -e "${GREEN}Backup completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi
