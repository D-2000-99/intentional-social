#!/bin/bash

# Restore script for Intentional Social database
# Usage: ./restore.sh <backup_file.sql.gz>

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo "Usage: ./restore.sh <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /home/deploy/backups/backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"
APP_DIR="/home/deploy/apps/Social_100"
COMPOSE_FILE="docker-compose.yml"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}WARNING: This will restore the database and overwrite all current data!${NC}"
echo -e "${YELLOW}Backup file: $BACKUP_FILE${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${YELLOW}Restore cancelled${NC}"
    exit 0
fi

echo -e "${YELLOW}Starting database restore...${NC}"

# Stop backend to prevent new connections
cd "$APP_DIR"
echo -e "${YELLOW}Stopping backend service...${NC}"
docker-compose -f "$COMPOSE_FILE" stop backend

# Decompress and restore
echo -e "${YELLOW}Restoring database...${NC}"
gunzip -c "$BACKUP_FILE" | docker-compose -f "$COMPOSE_FILE" exec -T db psql -U postgres intentional_social

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
    
    # Restart backend
    echo -e "${YELLOW}Restarting backend service...${NC}"
    docker-compose -f "$COMPOSE_FILE" start backend
    
    # Wait for backend to be healthy
    echo -e "${YELLOW}Waiting for backend to be ready...${NC}"
    sleep 5
    
    # Test health endpoint
    if docker-compose -f "$COMPOSE_FILE" exec backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        echo -e "${GREEN}Restore completed successfully!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Backend might not be fully ready yet${NC}"
        echo "Check logs: docker-compose logs backend"
        exit 0
    fi
else
    echo -e "${RED}✗ Restore failed!${NC}"
    
    # Try to restart backend anyway
    docker-compose -f "$COMPOSE_FILE" start backend
    exit 1
fi
