# Vultr Deployment Guide with Observability

This guide covers deploying your Intentional Social backend to Vultr with comprehensive observability.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Vultr Server Setup](#vultr-server-setup)
3. [Backend Deployment](#backend-deployment)
4. [Observability Stack](#observability-stack)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Maintenance & Operations](#maintenance--operations)

---

## Prerequisites

Before starting, ensure you have:

- [ ] Vultr account with payment method added
- [ ] Domain name (optional but recommended)
- [ ] SSH key pair generated
- [ ] Email service credentials (Gmail App Password or SendGrid)
- [ ] PostgreSQL database plan (managed or self-hosted)

---

## 🚀 Vultr Server Setup

### Step 1: Create a Vultr Instance

1. **Login to Vultr Dashboard**: https://my.vultr.com/

2. **Deploy New Server**:
   - Click "Deploy +" → "Deploy New Server"
   - **Choose Server Type**: Cloud Compute - Shared CPU (sufficient for 10-20 users)
   
3. **Server Configuration**:
   - **Location**: Choose closest to your users (e.g., New York, Tokyo, Frankfurt)
   - **Server Type**: Ubuntu 22.04 LTS (recommended)
   - **Server Size**: 
     - **Starter**: 1 vCPU, 2GB RAM, 55GB SSD - $12/month
     - **Recommended**: 2 vCPU, 4GB RAM, 80GB SSD - $18/month (for better performance)
   
4. **Add SSH Key**: 
   - Upload your SSH public key
   - Or generate one: `ssh-keygen -t ed25519 -C "your-email@example.com"`

5. **Server Settings**:
   - **Server Hostname**: `intentional-social-backend`
   - **Server Label**: `Production Backend`
   - **Enable Auto Backups**: Yes (recommended, +$1.20/month)
   - **Enable IPv6**: Optional

6. **Deploy Server** → Wait ~60 seconds for provisioning

### Step 2: Initial Server Configuration

```bash
# SSH into your server
ssh root@YOUR_SERVER_IP

# Update system packages
apt update && apt upgrade -y

# Install essential tools
apt install -y curl wget git vim ufw fail2ban htop

# Set timezone (optional)
timedatectl set-timezone Asia/Kolkata  # Or your timezone
```

### Step 3: Create Non-Root User

```bash
# Create user
adduser deploy
usermod -aG sudo deploy

# Copy SSH keys to new user
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

# Test SSH with new user (from your local machine)
ssh deploy@YOUR_SERVER_IP
```

### Step 4: Configure Firewall

```bash
# Enable UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # Backend (temporary, will be proxied later)
ufw enable

# Verify
ufw status
```

---

## 🐳 Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and back in for group changes to take effect
exit
ssh deploy@YOUR_SERVER_IP
```

---

## 📦 Backend Deployment

### Step 1: Set Up PostgreSQL

#### Option A: Managed PostgreSQL (Recommended)

Use Vultr Managed Database or external provider:

1. **Vultr Managed Database**:
   - Go to Products → Databases → Deploy Database
   - Choose PostgreSQL 16
   - Select region (same as your server)
   - Choose plan: Standalone 1 vCPU, 2GB RAM - $15/month
   - Note your connection string

2. **Alternative: DigitalOcean Managed PostgreSQL**:
   - Starter tier: $15/month
   - More reliable than self-hosting

#### Option B: Self-Hosted PostgreSQL on Same Server

```bash
# Using Docker Compose (included in deployment)
# See docker-compose.yml below
```

### Step 2: Clone Your Repository

```bash
# Create app directory
mkdir -p ~/apps
cd ~/apps

# Clone repository (replace with your repo URL)
git clone https://github.com/YOUR_USERNAME/Social_100.git
cd Social_100
```

### Step 3: Configure Environment Variables

```bash
# Create backend .env file
cd backend
cp .env.example .env
nano .env
```

**Production `.env` configuration**:

```bash
# Database (use managed PostgreSQL connection string)
DATABASE_URL=postgresql://username:password@host:port/dbname

# Security
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE_32_CHARS_MIN
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application
MAX_CONNECTIONS=100
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Email (Required)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# AWS S3 (if using image uploads)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1

# Environment
ENVIRONMENT=production
```

**Generate SECRET_KEY**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 4: Update Docker Compose for Production

Create `docker-compose.prod.yml` in root directory:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: intentional-social-backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - backend-logs:/app/logs
    restart: unless-stopped
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: postgres:16-alpine
    container_name: intentional-social-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-intentional_social}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - /var/log/nginx:/var/log/nginx
    restart: unless-stopped
    depends_on:
      - backend

volumes:
  postgres_data:
  backend-logs:
```

### Step 5: Configure Nginx

```bash
# Create nginx directory
mkdir -p nginx

# Create nginx.conf
nano nginx/nginx.conf
```

**nginx.conf**:

```nginx
events {
    worker_connections 1024;
}

http {
    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name api.yourdomain.com;  # Replace with your domain
        
        # Redirect to HTTPS (after SSL setup)
        # return 301 https://$server_name$request_uri;

        # Temporary: Allow HTTP (remove after SSL setup)
        location / {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint (no rate limit)
        location /health {
            proxy_pass http://backend;
            access_log off;
        }
    }

    # HTTPS configuration (add after SSL setup)
    # server {
    #     listen 443 ssl http2;
    #     server_name api.yourdomain.com;
    #
    #     ssl_certificate /etc/nginx/ssl/fullchain.pem;
    #     ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    #     ssl_protocols TLSv1.2 TLSv1.3;
    #     ssl_ciphers HIGH:!aNULL:!MD5;
    #
    #     location / {
    #         limit_req zone=api_limit burst=20 nodelay;
    #         proxy_pass http://backend;
    #         # ... same proxy settings as above
    #     }
    # }
}
```

### Step 6: Deploy Application

```bash
# Build and start services
cd ~/apps/Social_100
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### Step 7: Run Database Migrations

```bash
# Execute migrations in backend container
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify database
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d intentional_social -c "\dt"
```

### Step 8: Verify Deployment

```bash
# Test health endpoint
curl http://YOUR_SERVER_IP/health
# Should return: {"status":"ok"}

# Test from local machine
curl http://YOUR_SERVER_IP/health

# Check logs
docker-compose -f docker-compose.prod.yml logs backend
```

---

## 🔒 SSL/HTTPS Setup

### Install Certbot

```bash
# Install Certbot
sudo apt install certbot

# Stop nginx temporarily
docker-compose -f docker-compose.prod.yml stop nginx

# Get SSL certificate
sudo certbot certonly --standalone -d api.yourdomain.com

# Certificates will be saved to:
# /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/api.yourdomain.com/privkey.pem

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ~/apps/Social_100/nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ~/apps/Social_100/nginx/ssl/

# Update nginx.conf (uncomment HTTPS section, comment HTTP redirect)

# Restart nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

### Auto-Renew SSL Certificates

```bash
# Add cron job for auto-renewal
sudo crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * certbot renew --quiet --post-hook "docker-compose -f /home/deploy/apps/Social_100/docker-compose.prod.yml restart nginx"
```

---

## 📊 Observability Stack

### Logging Architecture

Your application already has logging configured in `app/main.py`. Let's enhance it for production.

### Step 1: Structured Logging

Update `backend/app/main.py` to use structured JSON logging:

```python
import logging
import json
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

# Configure logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
)

logger = logging.getLogger(__name__)
```

### Step 2: Add Request Logging Middleware

Add to `backend/app/main.py`:

```python
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host,
        }
    )
    
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
    )
    
    return response
```

### Step 3: Set Up Log Aggregation with Loki (Optional but Recommended)

Create `docker-compose.observability.yml`:

```yaml
version: '3.8'

services:
  loki:
    image: grafana/loki:2.9.0
    container_name: loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped

  promtail:
    image: grafana/promtail:2.9.0
    container_name: promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.0.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin  # Change this!
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

volumes:
  grafana_data:
  prometheus_data:
```

**Create `promtail-config.yml`**:

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

### Step 4: Add Prometheus Metrics

Install required packages:

```bash
# Add to backend/requirements.txt
prometheus-fastapi-instrumentator==6.1.0
```

Update `backend/app/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Intentional Social")

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)
```

**Create `prometheus.yml`**:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']
```

### Step 5: Start Observability Stack

```bash
# Start observability services
docker-compose -f docker-compose.observability.yml up -d

# Verify services
docker-compose -f docker-compose.observability.yml ps

# Access Grafana
# Open browser: http://YOUR_SERVER_IP:3000
# Login: admin / admin (change password immediately)
```

### Step 6: Configure Grafana Dashboards

1. **Add Data Sources**:
   - Go to Configuration → Data Sources
   - Add Prometheus: http://prometheus:9090
   - Add Loki: http://loki:3100

2. **Import Dashboards**:
   - FastAPI Dashboard: Import ID `12692`
   - PostgreSQL Dashboard: Import ID `9628`
   - Loki Logs Dashboard: Import ID `13639`

---

## 🔔 Monitoring & Alerting

### Option 1: Simple Monitoring (Free)

#### UptimeRobot

1. Sign up at https://uptimerobot.com (Free tier: 50 monitors)
2. Create HTTP monitor:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Intentional Social Backend
   - **URL**: https://api.yourdomain.com/health
   - **Monitoring Interval**: 5 minutes
3. Set up alerts:
   - Email notifications
   - Slack/Discord webhooks (optional)

#### Healthchecks.io

```bash
# Add to crontab for regular health checks
*/5 * * * * curl -fsS -m 10 --retry 5 https://hc-ping.com/YOUR_UUID

# Or add to your backend as a scheduled task
```

### Option 2: Comprehensive Monitoring (Self-Hosted)

#### Alertmanager Configuration

Create `alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'your-email@gmail.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'

route:
  receiver: 'email-alerts'
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'your-email@gmail.com'
        headers:
          Subject: '🚨 Alert: {{ .GroupLabels.alertname }}'
```

**Alert Rules (`alert.rules.yml`)**:

```yaml
groups:
  - name: backend_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: HighResponseTime
        expr: http_request_duration_seconds_bucket{le="1"} < 0.95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times"
          description: "95th percentile response time > 1s"

      - alert: ServiceDown
        expr: up{job="backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Backend service is down"
          description: "Backend has been down for more than 1 minute"

      - alert: HighCPUUsage
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is above 80%"
```

---

## 🔧 Maintenance & Operations

### Daily Operations

#### View Logs

```bash
# Backend logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Database logs
docker-compose -f docker-compose.prod.yml logs -f db

# Nginx logs
docker logs nginx-proxy -f

# All logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Monitor Resources

```bash
# Docker stats
docker stats

# System resources
htop

# Disk usage
df -h

# Database size
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d intentional_social -c "SELECT pg_size_pretty(pg_database_size('intentional_social'));"
```

### Backup Strategy

#### Automated Database Backups

Create `backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/deploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup database
docker-compose -f /home/deploy/apps/Social_100/docker-compose.prod.yml exec -T db pg_dump -U postgres intentional_social > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

```bash
# Make executable
chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
0 2 * * * /home/deploy/apps/Social_100/backup.sh >> /home/deploy/backups/backup.log 2>&1
```

#### Restore from Backup

```bash
# Stop backend
docker-compose -f docker-compose.prod.yml stop backend

# Restore database
gunzip -c backup_20241204_020000.sql.gz | docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres intentional_social

# Start backend
docker-compose -f docker-compose.prod.yml start backend
```

### Update Deployment

```bash
# Pull latest code
cd ~/apps/Social_100
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Run migrations if needed
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

---

## 📈 Cost Breakdown

### Vultr Costs
- **Server (2 vCPU, 4GB RAM)**: $18/month
- **Auto Backups**: $1.80/month
- **Bandwidth**: Included (2TB)

### Optional Services
- **Managed PostgreSQL (Vultr)**: $15/month
- **Domain**: $10-15/year
- **Email (SendGrid)**: Free tier (100 emails/day)

**Total**: ~$35-50/month with managed database, ~$20/month self-hosted

---

## 🎯 Observability Summary

### What You Get:

1. **Structured Logging**: JSON logs for easy parsing
2. **Metrics**: Prometheus metrics for performance monitoring
3. **Dashboards**: Grafana dashboards for visualization
4. **Alerts**: Real-time alerts for issues
5. **Uptime Monitoring**: UptimeRobot for availability checks
6. **Log Aggregation**: Loki for centralized log management

### Key Metrics to Monitor:

- ✅ Request rate (requests/sec)
- ✅ Error rate (5xx errors)
- ✅ Response time (p50, p95, p99)
- ✅ Database connections
- ✅ CPU & Memory usage
- ✅ Disk space
- ✅ Uptime percentage

### Access Observability:

- **Grafana**: http://YOUR_SERVER_IP:3000
- **Prometheus**: http://YOUR_SERVER_IP:9090
- **Application**: https://api.yourdomain.com

---

## 🆘 Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check environment variables
docker-compose -f docker-compose.prod.yml exec backend env

# Restart service
docker-compose -f docker-compose.prod.yml restart backend
```

### High Memory Usage
```bash
# Check container stats
docker stats

# Restart containers
docker-compose -f docker-compose.prod.yml restart

# Check logs for memory leaks
docker-compose -f docker-compose.prod.yml logs backend | grep -i "memory"
```

### Database Connection Issues
```bash
# Test database connection
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.db import engine; print(engine.connect())"

# Check database logs
docker-compose -f docker-compose.prod.yml logs db

# Verify DATABASE_URL
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL
```

---

## ✅ Post-Deployment Checklist

- [ ] Server deployed and accessible
- [ ] Docker and Docker Compose installed
- [ ] Application deployed and running
- [ ] Database migrations completed
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Backups automated
- [ ] Monitoring configured (UptimeRobot + Grafana)
- [ ] Alerts set up
- [ ] Logs aggregated
- [ ] Health checks passing
- [ ] Domain configured (if applicable)
- [ ] Email service tested
- [ ] Documentation updated

---

**Deployment Time**: 4-6 hours  
**Difficulty**: Medium to Advanced  
**Recommended for**: Production deployments requiring full control and observability

Good luck with your deployment! 🚀
