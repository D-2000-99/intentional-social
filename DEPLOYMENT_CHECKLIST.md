# Vultr Deployment Checklist

Use this checklist to track your deployment progress.

## Pre-Deployment Preparation

### Account Setup
- [ ] Vultr account created
- [ ] Payment method added
- [ ] SSH key pair generated locally
- [ ] Domain purchased (optional but recommended)

### Service Accounts
- [ ] Email service configured (Gmail App Password or SendGrid)
- [ ] AWS S3 bucket created (if using image uploads)
- [ ] Git repository accessible

### Documentation Review
- [ ] Read VULTR_DEPLOYMENT_GUIDE.md
- [ ] Review VULTR_DEPLOYMENT_SUMMARY.md
- [ ] Understand ARCHITECTURE.md
- [ ] Bookmark VULTR_QUICK_REFERENCE.md

---

## Phase 1: Server Setup ⏱️ 1-2 hours

### Create Vultr Instance
- [ ] Deploy server (2 vCPU, 4GB RAM recommended)
- [ ] Choose location closest to users
- [ ] Upload SSH key
- [ ] Enable auto-backups ($1.80/month)
- [ ] Note server IP address: `_________________`

### Initial Server Configuration
```bash
ssh root@YOUR_SERVER_IP
```
- [ ] Update system: `apt update && apt upgrade -y`
- [ ] Install essential tools: `apt install -y curl wget git vim ufw fail2ban htop`
- [ ] Set timezone: `timedatectl set-timezone YOUR_TIMEZONE`
- [ ] Create deploy user
- [ ] Add deploy user to sudo and docker groups
- [ ] Test SSH with deploy user

### Configure Firewall
- [ ] Set UFW defaults
- [ ] Allow SSH (port 22)
- [ ] Allow HTTP (port 80)
- [ ] Allow HTTPS (port 443)
- [ ] Enable UFW
- [ ] Verify firewall status: `ufw status`

### Install Docker
- [ ] Install Docker: `curl -fsSL https://get.docker.com | sh`
- [ ] Add user to docker group
- [ ] Install Docker Compose
- [ ] Verify Docker: `docker --version`
- [ ] Verify Docker Compose: `docker-compose --version`
- [ ] Log out and back in

---

## Phase 2: Application Deployment ⏱️ 2-3 hours

### Clone Repository
- [ ] Create apps directory: `mkdir -p ~/apps`
- [ ] Clone repository to `~/apps/Social_100`
- [ ] Verify files present: `ls -la ~/apps/Social_100`

### Database Setup

**Option A: Managed Database (Recommended)**
- [ ] Create managed PostgreSQL instance
- [ ] Note connection string: `_________________`
- [ ] Test connection from server

**Option B: Self-Hosted Database**
- [ ] Will use Docker Compose PostgreSQL
- [ ] Set POSTGRES_USER, POSTGRES_PASSWORD in .env

### Configure Environment Variables

**Backend Configuration**
```bash
cd ~/apps/Social_100/backend
cp .env.example .env
nano .env
```

- [ ] Set `DATABASE_URL` (from managed DB or self-hosted)
- [ ] Generate and set `SECRET_KEY`: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Set `SECRET_KEY`: `_________________________________`
- [ ] Set `ALGORITHM=HS256`
- [ ] Set `ACCESS_TOKEN_EXPIRE_MINUTES=60`
- [ ] Set `MAX_CONNECTIONS=100`
- [ ] Set `CORS_ORIGINS` (will update after frontend deployment)
- [ ] Configure SMTP settings:
  - [ ] `SMTP_SERVER`
  - [ ] `SMTP_PORT`
  - [ ] `SMTP_USERNAME`
  - [ ] `SMTP_PASSWORD`
  - [ ] `SMTP_FROM_EMAIL`
- [ ] Configure AWS S3 (if using):
  - [ ] `AWS_ACCESS_KEY_ID`
  - [ ] `AWS_SECRET_ACCESS_KEY`
  - [ ] `AWS_BUCKET_NAME`
  - [ ] `AWS_REGION`
- [ ] Set `ENVIRONMENT=production`

### Configure Nginx
```bash
nano ~/apps/Social_100/nginx/nginx.conf
```
- [ ] Update `server_name` with your domain (or IP)
- [ ] Review rate limiting settings
- [ ] Save configuration

### Deploy Application
```bash
cd ~/apps/Social_100
docker-compose -f docker-compose.prod.yml up -d
```
- [ ] Build and start containers
- [ ] Verify all containers running: `docker-compose -f docker-compose.prod.yml ps`
- [ ] Check backend logs: `docker-compose -f docker-compose.prod.yml logs backend`

### Run Database Migrations
```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```
- [ ] Migrations completed successfully
- [ ] Verify tables created: 
  ```bash
  docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d intentional_social -c "\dt"
  ```

### Test Backend
- [ ] Test health endpoint: `curl http://YOUR_SERVER_IP/health`
- [ ] Test metrics endpoint: `curl http://YOUR_SERVER_IP/metrics`
- [ ] Check response: Should see `{"status":"ok"}` for health
- [ ] Check logs for errors

---

## Phase 3: SSL/HTTPS Setup ⏱️ 30-60 minutes

### Domain Configuration (If using domain)
- [ ] Point domain A record to server IP
- [ ] Point subdomain (api.yourdomain.com) to server IP
- [ ] Wait for DNS propagation (check: `dig api.yourdomain.com`)

### Install Certbot
```bash
sudo apt install certbot
```
- [ ] Certbot installed

### Obtain SSL Certificate
```bash
# Stop nginx temporarily
docker-compose -f docker-compose.prod.yml stop nginx

# Get certificate
sudo certbot certonly --standalone -d api.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ~/apps/Social_100/nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ~/apps/Social_100/nginx/ssl/
```
- [ ] SSL certificate obtained
- [ ] Certificates copied to nginx directory
- [ ] Set proper permissions: `sudo chmod 644 ~/apps/Social_100/nginx/ssl/*`

### Update Nginx Configuration
```bash
nano ~/apps/Social_100/nginx/nginx.conf
```
- [ ] Uncomment HTTPS server block
- [ ] Update certificate paths
- [ ] Enable HTTP → HTTPS redirect
- [ ] Save configuration

### Restart Nginx
```bash
docker-compose -f docker-compose.prod.yml up -d nginx
```
- [ ] Nginx restarted successfully
- [ ] Test HTTPS: `curl https://api.yourdomain.com/health`

### Auto-Renew SSL
```bash
sudo crontab -e
# Add: 0 2 * * * certbot renew --quiet --post-hook "docker-compose -f /home/deploy/apps/Social_100/docker-compose.prod.yml restart nginx"
```
- [ ] Cron job added for SSL renewal

---

## Phase 4: Observability Setup ⏱️ 1-2 hours

### Configure Observability Stack

**Update Alertmanager Configuration**
```bash
nano ~/apps/Social_100/observability/alertmanager.yml
```
- [ ] Set SMTP server
- [ ] Set email address for alerts
- [ ] Set SMTP credentials
- [ ] Save configuration

### Deploy Observability Services
```bash
cd ~/apps/Social_100
docker-compose -f docker-compose.observability.yml up -d
```
- [ ] All observability containers started
- [ ] Verify containers: `docker-compose -f docker-compose.observability.yml ps`

### Configure Grafana

**Access Grafana**
- [ ] Open browser: `http://YOUR_SERVER_IP:3000`
- [ ] Login: admin / admin
- [ ] Change default password
- [ ] New password: `_________________`

**Add Data Sources** (Should be auto-provisioned)
- [ ] Verify Prometheus datasource exists
- [ ] Verify Loki datasource exists
- [ ] Test datasources (should show green checkmark)

**Import Dashboards**
- [ ] Import FastAPI dashboard (ID: 12692)
- [ ] Import PostgreSQL dashboard (ID: 9628)
- [ ] Import Node Exporter dashboard (ID: 1860)
- [ ] Create custom dashboard for your app

### Test Observability

**Prometheus**
- [ ] Access: `http://YOUR_SERVER_IP:9090`
- [ ] Check targets are up: Status → Targets
- [ ] Verify all targets show "UP"
- [ ] Run sample query: `up`

**Loki Logs**
- [ ] Open Grafana → Explore
- [ ] Select Loki datasource
- [ ] Query logs: `{container="intentional-social-backend"}`
- [ ] Verify logs appear

**Alertmanager**
- [ ] Access: `http://YOUR_SERVER_IP:9093`
- [ ] Verify configuration loaded
- [ ] Send test alert

### Verify Metrics Collection
```bash
# Check backend metrics
curl http://YOUR_SERVER_IP/metrics

# Should see Prometheus format metrics
```
- [ ] Metrics endpoint working
- [ ] Prometheus scraping metrics

---

## Phase 5: Backup & Maintenance ⏱️ 30 minutes

### Set Up Automated Backups
```bash
cd ~/apps/Social_100

# Make scripts executable
chmod +x backup.sh restore.sh

# Test backup manually
./backup.sh
```
- [ ] Backup script executed successfully
- [ ] Backup file created in `/home/deploy/backups/`
- [ ] Backup file compressed

### Schedule Automated Backups
```bash
crontab -e
# Add: 0 2 * * * /home/deploy/apps/Social_100/backup.sh >> /home/deploy/backups/backup.log 2>&1
```
- [ ] Cron job added
- [ ] Verify cron job: `crontab -l`

### Test Restore Process
```bash
# List backups
ls -lh /home/deploy/backups/

# Test restore (use most recent backup)
./restore.sh /home/deploy/backups/backup_YYYYMMDD_HHMMSS.sql.gz
```
- [ ] Restore process tested
- [ ] Backend restarted successfully
- [ ] Data verified

### External Backup (Optional but Recommended)
- [ ] Set up S3/Backblaze B2 bucket
- [ ] Create script to upload backups
- [ ] Test external backup
- [ ] Schedule external backup

---

## Phase 6: Monitoring & Alerts ⏱️ 30 minutes

### Set Up External Monitoring

**UptimeRobot (Free)**
- [ ] Create account: https://uptimerobot.com
- [ ] Add HTTP monitor for `https://api.yourdomain.com/health`
- [ ] Set check interval: 5 minutes
- [ ] Add alert contacts (email, SMS)
- [ ] Verify monitor is working

**Healthchecks.io (Optional)**
- [ ] Create account: https://healthchecks.io
- [ ] Create check for backup script
- [ ] Add webhook to backup script

### Test Alerting

**Trigger Test Alert**
```bash
# Stop backend to trigger alert
docker-compose -f docker-compose.prod.yml stop backend

# Wait 1-2 minutes for alert
# Check email for alert

# Restart backend
docker-compose -f docker-compose.prod.yml start backend
```
- [ ] Alert email received
- [ ] Alert format is correct
- [ ] Recovery email received

### Review Alert Rules
```bash
# Check Prometheus alerts
curl http://YOUR_SERVER_IP:9090/api/v1/alerts
```
- [ ] Alert rules loaded
- [ ] No unexpected alerts firing

---

## Phase 7: Security Hardening ⏱️ 30 minutes

### Firewall Configuration
- [ ] Verify UFW status: `sudo ufw status`
- [ ] Verify only required ports open (22, 80, 443)
- [ ] Remove port 8000 if exposed: `sudo ufw delete allow 8000`

### SSH Hardening (Optional but Recommended)
```bash
sudo nano /etc/ssh/sshd_config
```
- [ ] Disable root login: `PermitRootLogin no`
- [ ] Disable password authentication: `PasswordAuthentication no`
- [ ] Restart SSH: `sudo systemctl restart sshd`
- [ ] Test SSH with new settings (keep current session open!)

### Fail2ban Configuration
- [ ] Verify fail2ban running: `sudo systemctl status fail2ban`
- [ ] Configure jail for nginx (optional)
- [ ] Configure jail for SSH

### Review Security Settings
- [ ] CORS origins set correctly in backend .env
- [ ] Rate limiting configured in nginx
- [ ] Security headers enabled in backend
- [ ] Database not exposed publicly
- [ ] SSL/HTTPS working
- [ ] Strong passwords used everywhere

---

## Phase 8: Testing & Validation ⏱️ 1 hour

### API Testing
- [ ] Test health endpoint: `curl https://api.yourdomain.com/health`
- [ ] Test user registration (use Postman or curl)
- [ ] Verify email OTP received
- [ ] Complete registration flow
- [ ] Test login
- [ ] Test creating post
- [ ] Test connection request
- [ ] Test feed retrieval

### Load Testing (Optional)
```bash
# Install ab (Apache Bench)
sudo apt install apache2-utils

# Simple load test
ab -n 100 -c 10 https://api.yourdomain.com/health
```
- [ ] Server handles concurrent requests
- [ ] Response times acceptable
- [ ] No errors in logs

### Monitoring Validation
- [ ] View request rate in Grafana
- [ ] View response times in Grafana
- [ ] Check database metrics
- [ ] Check system resources
- [ ] Verify logs appear in Loki

### Stress Test Observability
- [ ] Generate some API traffic
- [ ] Watch metrics update in real-time
- [ ] Check logs streaming in Grafana
- [ ] Verify alerts don't fire under normal load

---

## Phase 9: Documentation ⏱️ 30 minutes

### Create Runbook
```bash
nano ~/apps/Social_100/RUNBOOK.md
```

Document:
- [ ] How to access the server
- [ ] How to check service status
- [ ] How to view logs
- [ ] How to restart services
- [ ] How to run migrations
- [ ] How to restore from backup
- [ ] Emergency contact information
- [ ] Common issues and solutions

### Update Project README
- [ ] Add deployment information
- [ ] Add monitoring dashboards URLs
- [ ] Add credentials (securely!)
- [ ] Add maintenance schedule

### Save Important Information
Store securely (password manager):
- [ ] Server IP: `_________________`
- [ ] Root password: `_________________`
- [ ] Deploy user password: `_________________`
- [ ] Database password: `_________________`
- [ ] Grafana password: `_________________`
- [ ] Domain registrar login
- [ ] SSL certificate location
- [ ] Backup locations

---

## Phase 10: Go Live! ⏱️ 1 hour

### Pre-Launch Checklist
- [ ] All services running
- [ ] All tests passing
- [ ] Monitoring configured
- [ ] Alerts working
- [ ] Backups automated
- [ ] SSL working
- [ ] Security hardened
- [ ] Documentation complete

### Update Frontend
```bash
# In frontend .env or .env.production
VITE_API_URL=https://api.yourdomain.com
```
- [ ] Frontend configured with production API URL
- [ ] Frontend deployed
- [ ] Frontend → Backend communication working

### Final Verification
- [ ] End-to-end user flow works
- [ ] Email verification works
- [ ] All features functional
- [ ] Performance acceptable
- [ ] Monitoring active
- [ ] Alerts configured

### Announce Launch
- [ ] Notify users
- [ ] Share access URLs
- [ ] Provide documentation
- [ ] Set expectations

---

## Post-Launch Monitoring (First Week)

### Daily Checks
- [ ] Check Grafana dashboards
- [ ] Review error logs
- [ ] Check disk space
- [ ] Verify backups running
- [ ] Monitor user feedback

### Weekly Checks
- [ ] Review performance trends
- [ ] Check alert history
- [ ] Review resource usage
- [ ] Plan optimizations if needed
- [ ] Update documentation

---

## Troubleshooting Reference

### Service Won't Start
1. Check logs: `docker-compose -f docker-compose.prod.yml logs SERVICE_NAME`
2. Check environment variables
3. Check disk space: `df -h`
4. Restart service: `docker-compose -f docker-compose.prod.yml restart SERVICE_NAME`

### Database Issues
1. Check connection: `docker-compose -f docker-compose.prod.yml ps db`
2. Check logs: `docker-compose -f docker-compose.prod.yml logs db`
3. Check disk space
4. Verify DATABASE_URL in .env

### Monitoring Issues
1. Check Prometheus targets: http://YOUR_SERVER_IP:9090/targets
2. Check Grafana datasources
3. Restart observability stack

### High Resource Usage
1. Check `docker stats`
2. Check `htop`
3. Review slow queries in database
4. Optimize or scale up

---

## Success Criteria

Your deployment is successful when:
- ✅ All API endpoints responding
- ✅ HTTPS working with valid certificate
- ✅ Monitoring dashboards showing data
- ✅ Alerts configured and tested
- ✅ Backups running automatically
- ✅ Users can register and use the platform
- ✅ Performance meets requirements
- ✅ Documentation complete

---

## Estimated Total Time: 6-10 hours

**Breakdown:**
- Server setup: 1-2 hours
- Application deployment: 2-3 hours
- Observability: 1-2 hours
- Security & testing: 1-2 hours
- Documentation: 30-60 minutes
- Contingency: 1-2 hours

---

**Deployment Date**: ___________________  
**Deployed By**: ___________________  
**Server IP**: ___________________  
**Domain**: ___________________  
**Status**: [ ] In Progress [ ] Completed

Good luck with your deployment! 🚀
