# Vultr Deployment - Quick Reference

This is a quick reference guide for deploying and managing your Intentional Social backend on Vultr.

## 📚 Documentation

- **[Full Deployment Guide](./VULTR_DEPLOYMENT_GUIDE.md)** - Comprehensive step-by-step guide
- **[Quick Start Guide](./DEPLOYMENT_QUICK_START.md)** - Fast deployment options
- **[Production Plan](./PRODUCTION_DEPLOYMENT_PLAN.md)** - Detailed production readiness

## 🚀 Quick Deployment Steps

### 1. Set Up Vultr Server
```bash
# After creating Vultr instance, SSH in
ssh root@YOUR_SERVER_IP

# Update and install essentials
apt update && apt upgrade -y
apt install -y docker.io docker-compose git

# Create deploy user
adduser deploy
usermod -aG sudo,docker deploy
```

### 2. Clone and Configure
```bash
# Switch to deploy user
su - deploy

# Clone repository
git clone YOUR_REPO_URL ~/apps/Social_100
cd ~/apps/Social_100

# Configure environment
cd backend
cp .env.example .env
nano .env  # Edit with your values
```

### 3. Deploy Application
```bash
# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### 4. Set Up Observability
```bash
# Start observability stack
docker-compose -f docker-compose.observability.yml up -d

# Access Grafana
# Open browser: http://YOUR_SERVER_IP:3000
# Login: admin / admin
```

## 📊 Observability Access

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | `http://YOUR_SERVER_IP:3000` | admin / admin |
| **Prometheus** | `http://YOUR_SERVER_IP:9090` | - |
| **Alertmanager** | `http://YOUR_SERVER_IP:9093` | - |
| **Backend API** | `http://YOUR_SERVER_IP` | - |
| **Metrics Endpoint** | `http://YOUR_SERVER_IP/metrics` | - |

## 🔧 Common Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Backend only
docker-compose -f docker-compose.prod.yml logs -f backend

# Database only
docker-compose -f docker-compose.prod.yml logs -f db
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart backend only
docker-compose -f docker-compose.prod.yml restart backend
```

### Database Management
```bash
# Backup database
./backup.sh

# Restore from backup
./restore.sh /path/to/backup.sql.gz

# Access database shell
docker-compose -f docker-compose.prod.yml exec db psql -U postgres intentional_social
```

### Update Deployment
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Run new migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 📈 Key Metrics to Monitor

### Application Health
- **Uptime**: Should be 99.9%+
- **Response Time**: p95 < 500ms, p99 < 1s
- **Error Rate**: < 1% (5xx errors)
- **Request Rate**: Monitor for anomalies

### System Resources
- **CPU Usage**: < 70% average
- **Memory Usage**: < 80%
- **Disk Space**: > 20% free
- **Database Connections**: < 80 connections

### Database
- **Query Performance**: Average < 100ms
- **Connection Pool**: < 80% utilization
- **Database Size**: Monitor growth rate

## 🔔 Alerts Configuration

Edit `observability/alertmanager.yml` to configure email alerts:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'your-email@gmail.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'
```

## 🛠️ Troubleshooting

### Backend Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec backend env | grep -E 'DATABASE_URL|SECRET_KEY'

# Restart
docker-compose -f docker-compose.prod.yml restart backend
```

### Database Connection Errors
```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Test connection
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.db import engine; print(engine.connect())"

# Restart database
docker-compose -f docker-compose.prod.yml restart db
```

### High Memory Usage
```bash
# Check container stats
docker stats

# Restart services to free memory
docker-compose -f docker-compose.prod.yml restart
```

### SSL Certificate Issues
```bash
# Renew certificate
sudo certbot renew

# Copy to nginx
sudo cp /etc/letsencrypt/live/api.yourdomain.com/*.pem ~/apps/Social_100/nginx/ssl/

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## 📦 Backup Schedule

Automated backups run daily at 2 AM via cron:

```bash
# View cron jobs
crontab -l

# Add backup job
crontab -e
# Add: 0 2 * * * /home/deploy/apps/Social_100/backup.sh
```

Backups are stored in `/home/deploy/backups/` and kept for 7 days.

## 🔒 Security Checklist

- [x] Firewall configured (UFW)
- [x] SSL/HTTPS enabled
- [x] Security headers set
- [x] Rate limiting enabled
- [x] Database password secured
- [x] Regular backups automated
- [ ] Update Grafana default password
- [ ] Configure Alertmanager email
- [ ] Set up external monitoring (UptimeRobot)

## 💰 Monthly Costs

| Service | Cost |
|---------|------|
| Vultr Server (2 vCPU, 4GB) | $18/month |
| Auto Backups | $1.80/month |
| **Total** | **~$20/month** |

Optional:
- Managed PostgreSQL: +$15/month
- Domain: ~$1/month (annual)

## 📞 Support

For issues:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs -f`
2. Check Grafana dashboards: `http://YOUR_SERVER_IP:3000`
3. Review full deployment guide: [VULTR_DEPLOYMENT_GUIDE.md](./VULTR_DEPLOYMENT_GUIDE.md)

## 🎯 Health Check

Quick health check commands:

```bash
# Test API
curl http://YOUR_SERVER_IP/health

# Test metrics
curl http://YOUR_SERVER_IP/metrics

# Check all services
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.observability.yml ps

# View resource usage
docker stats --no-stream
```

---

**Last Updated**: 2025-12-04  
**Platform**: Vultr  
**Environment**: Production
