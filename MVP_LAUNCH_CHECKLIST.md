# MVP Launch Checklist - Quick Reference

**Target:** 10-20 beta users for 2 weeks  
**Status:** Ready for deployment  
**Estimated Setup Time:** 4-6 hours

---

## 🚀 Pre-Launch Checklist

### 1. Backend Deployment (2-3 hours)

#### VPS Setup
- [ ] Create VPS (DigitalOcean/Linode - $12/month, 2GB RAM, 1 vCPU)
- [ ] SSH into VPS: `ssh root@YOUR_VPS_IP`
- [ ] Update system: `apt update && apt upgrade -y`
- [ ] Install Docker: `curl -fsSL https://get.docker.com | sh`
- [ ] Install Docker Compose
- [ ] Configure firewall (UFW): ports 22, 80, 443
- [ ] Create non-root user: `adduser deploy`

#### Code Deployment
- [ ] Clone repository to VPS: `git clone https://github.com/YOUR_USERNAME/Social_100.git`
- [ ] Navigate to project: `cd Social_100`
- [ ] Create backend/.env file with all required variables
- [ ] Generate SECRET_KEY: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Set .env permissions: `chmod 600 backend/.env`

#### Database Setup
- [ ] Start Docker services: `docker-compose up -d`
- [ ] **CRITICAL:** Run migrations: `docker-compose exec backend alembic upgrade head`
- [ ] Verify database: `docker-compose exec db psql -U postgres -c "SELECT 1"`
- [ ] Test health endpoint: `curl http://localhost:8000/health`

#### Nginx & SSL
- [ ] Install Nginx: `apt install -y nginx`
- [ ] Configure reverse proxy (see VPS_SETUP_GUIDE.md)
- [ ] Install Certbot: `apt install -y certbot python3-certbot-nginx`
- [ ] Get SSL certificate: `certbot --nginx -d api.yourdomain.com`
- [ ] Test HTTPS: `curl https://api.yourdomain.com/health`

### 2. Frontend Deployment (1 hour)

#### Cloudflare Pages Setup
- [ ] Go to Cloudflare Dashboard → Workers & Pages
- [ ] Connect GitHub repository
- [ ] Configure build settings:
  - Build command: `cd frontend && npm install && npm run build`
  - Build output: `frontend/dist`
- [ ] Add environment variable: `VITE_API_URL=https://api.yourdomain.com`
- [ ] Deploy and wait for build to complete
- [ ] Test deployment URL

#### CORS Configuration
- [ ] Update backend/.env with frontend URL:
  ```bash
  CORS_ORIGINS=https://your-app.pages.dev,https://app.yourdomain.com
  ```
- [ ] Restart backend: `docker-compose restart backend`
- [ ] Test CORS from browser console

### 3. Email Configuration (30 minutes)

#### Gmail Setup
- [ ] Enable 2FA on Gmail account
- [ ] Generate app password: https://myaccount.google.com/apppasswords
- [ ] Add to backend/.env:
  ```bash
  SMTP_SERVER=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USERNAME=your-email@gmail.com
  SMTP_PASSWORD=your-app-password
  SMTP_FROM_EMAIL=your-email@gmail.com
  ```
- [ ] Restart backend: `docker-compose restart backend`
- [ ] **Test email sending:** Register a test user and verify OTP arrives

### 4. Backup Setup (30 minutes)

- [ ] Test backup script: `./backup.sh`
- [ ] Set up cron job for daily backups:
  ```bash
  crontab -e
  # Add: 0 2 * * * /path/to/Social_100/backup.sh
  ```
- [ ] Test restore procedure: `./restore.sh backup_YYYYMMDD.sql`
- [ ] Set up off-site backup storage (S3, Backblaze B2)

### 5. Monitoring Setup (30 minutes)

- [ ] Set up UptimeRobot or Pingdom for health checks
- [ ] Configure alerts for downtime
- [ ] (Optional) Set up Sentry for error tracking
- [ ] Verify Prometheus metrics: `curl https://api.yourdomain.com/metrics`

---

## 🧪 Testing Checklist (1-2 hours)

### End-to-End Testing

#### Authentication Flow
- [ ] Register new user (test email OTP)
- [ ] Verify email arrives within 1 minute
- [ ] Complete registration with OTP
- [ ] Login with credentials
- [ ] Logout and login again
- [ ] Test "forgot password" (if implemented)

#### Connection System
- [ ] Send connection request to another user
- [ ] Accept connection request
- [ ] Reject connection request
- [ ] View connections list
- [ ] Test 100-connection limit (optional - time-consuming)

#### Posts & Feed
- [ ] Create text-only post
- [ ] Create post with photo
- [ ] Create post with multiple photos
- [ ] Test audience controls (all, private, tags)
- [ ] View feed (should show connected users' posts)
- [ ] Verify chronological order

#### Comments
- [ ] Add comment to post
- [ ] Reply to comment
- [ ] View comment thread
- [ ] Delete own comment

#### Tags
- [ ] Create tag
- [ ] Tag a connection
- [ ] Create post with tag-based audience
- [ ] Verify only tagged users see post

#### Performance
- [ ] Feed loads in <500ms
- [ ] Post creation completes in <1 second
- [ ] Photo upload works (test with 5MB image)
- [ ] No console errors in browser DevTools

#### Mobile Testing
- [ ] Test on mobile browser (iOS/Android)
- [ ] Verify responsive design
- [ ] Test photo upload from mobile
- [ ] Test all core features on mobile

---

## 📊 Health Check Dashboard

### Daily Checks (5 minutes)

```bash
# 1. Check services are running
docker-compose ps

# 2. Check health endpoints
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/health/db

# 3. Check recent logs for errors
docker-compose logs --tail=50 backend | grep ERROR

# 4. Check disk space
df -h

# 5. Check database size
docker-compose exec db psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('intentional_social'));"
```

### Weekly Checks (30 minutes)

- [ ] Review all error logs
- [ ] Check backup status (verify last backup exists)
- [ ] Review user feedback
- [ ] Monitor database growth
- [ ] Check for security updates: `apt update && apt list --upgradable`
- [ ] Review Prometheus metrics (if configured)

---

## 🐛 Common Issues & Quick Fixes

### Issue: Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common causes:
# 1. Database not ready → Wait 30 seconds and retry
# 2. Migration failed → Check migration logs
# 3. Port conflict → Check if port 8000 is in use: lsof -i :8000
```

### Issue: Email not sending
```bash
# 1. Verify SMTP credentials in .env
# 2. Check backend logs for SMTP errors
docker-compose logs backend | grep SMTP

# 3. Test SMTP connection manually
# 4. Check Gmail app password is correct
# 5. Verify Gmail hasn't blocked the app password
```

### Issue: Frontend can't connect to backend
```bash
# 1. Check CORS configuration
# 2. Verify VITE_API_URL is correct
# 3. Check backend is accessible
curl https://api.yourdomain.com/health

# 4. Check browser console for CORS errors
# 5. Verify SSL certificate is valid
```

### Issue: Database migration failed
```bash
# 1. Check migration logs
docker-compose logs backend

# 2. Rollback migration
docker-compose exec backend alembic downgrade -1

# 3. Fix migration file
# 4. Re-run migration
docker-compose exec backend alembic upgrade head
```

### Issue: Slow performance
```bash
# 1. Check database indexes are applied
docker-compose exec db psql -U postgres intentional_social -c "\d posts"

# 2. Check for slow queries in logs
docker-compose logs backend | grep "slow query"

# 3. Monitor database connections
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Check server resources
htop  # or top
```

---

## 📈 Success Metrics to Track

### Technical Metrics

| Metric | Target | How to Check |
|--------|--------|--------------|
| Uptime | >99% | UptimeRobot dashboard |
| Response Time (p95) | <500ms | Prometheus metrics or logs |
| Error Rate | <1% | `docker-compose logs backend \| grep ERROR \| wc -l` |
| Database Size | <500MB | `SELECT pg_size_pretty(pg_database_size('intentional_social'));` |

### User Metrics

| Metric | Target | How to Track |
|--------|--------|--------------|
| Registration Success | >90% | Count successful registrations vs attempts |
| Daily Active Users | >50% | Count unique logins per day |
| Posts per User | >2/week | Query posts table |
| Connection Acceptance | >60% | Count accepted vs sent requests |

---

## 🎯 Beta Testing Timeline

### Week 1: Soft Launch (3-5 users)

**Day 1-2:**
- [ ] Invite 3-5 close contacts
- [ ] Send onboarding email with instructions
- [ ] Monitor closely for critical bugs
- [ ] Respond to issues within 2 hours

**Day 3-5:**
- [ ] Collect initial feedback
- [ ] Fix critical bugs
- [ ] Deploy improvements
- [ ] Verify stability

**Day 6-7:**
- [ ] Review metrics
- [ ] Prepare for wider beta
- [ ] Update documentation based on feedback

### Week 2: Expanded Beta (10-20 users)

**Day 8-10:**
- [ ] Invite additional 5-15 users
- [ ] Send welcome email
- [ ] Monitor performance under load
- [ ] Respond to issues within 24 hours

**Day 11-14:**
- [ ] Collect comprehensive feedback
- [ ] Track usage patterns
- [ ] Identify most-used features
- [ ] Plan improvements

---

## 📞 Emergency Contacts

**VPS Provider Support:**
- DigitalOcean: https://www.digitalocean.com/support
- Linode: https://www.linode.com/support

**Cloudflare Support:**
- Community: https://community.cloudflare.com/
- Status: https://www.cloudflarestatus.com/

**Domain Registrar:**
- [Your registrar support link]

**Emergency Procedures:**
1. Check status pages first
2. Review logs: `docker-compose logs backend`
3. Restart services: `docker-compose restart`
4. Restore from backup if needed: `./restore.sh`
5. Contact VPS provider if infrastructure issue

---

## ✅ Final Pre-Launch Verification

### Critical Checks (Must Pass)

- [ ] Health endpoint responds: `curl https://api.yourdomain.com/health`
- [ ] Database migration applied: Check for performance indexes
- [ ] Email sending works: Test OTP delivery
- [ ] Frontend loads: Visit https://your-app.pages.dev
- [ ] User can register and login
- [ ] User can create post
- [ ] User can send connection request
- [ ] SSL certificate is valid (no browser warnings)
- [ ] Backups are configured and tested
- [ ] Monitoring is set up (UptimeRobot)

### Optional Checks (Recommended)

- [ ] Redis caching enabled (optional for 10-20 users)
- [ ] Grafana dashboards configured
- [ ] Error tracking (Sentry) set up
- [ ] CI/CD pipeline configured
- [ ] Load testing performed

---

## 🎉 Launch Day Checklist

### Morning (Before Invites)

- [ ] Verify all services are running
- [ ] Check health endpoints
- [ ] Review logs for any errors
- [ ] Test registration flow one more time
- [ ] Verify email sending
- [ ] Check disk space
- [ ] Verify backups are working

### Send Invites

- [ ] Send welcome email to beta users
- [ ] Include:
  - Registration link
  - Quick start guide
  - Support contact (email/Discord)
  - Feedback form link
  - Expected response time

### Throughout the Day

- [ ] Monitor logs every 2 hours
- [ ] Check for error spikes
- [ ] Respond to user questions quickly
- [ ] Track registration success rate
- [ ] Note any issues for evening review

### Evening Review

- [ ] Review all logs
- [ ] Check metrics dashboard
- [ ] Respond to all user feedback
- [ ] Plan fixes for next day
- [ ] Send update to users if needed

---

## 📝 Quick Reference Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart backend
docker-compose restart backend

# View logs (live)
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend

# Run migration
docker-compose exec backend alembic upgrade head

# Backup database
./backup.sh

# Restore database
./restore.sh backup_YYYYMMDD.sql

# Check database size
docker-compose exec db psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('intentional_social'));"

# Check active connections
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Rebuild and restart
docker-compose up -d --build

# Check health
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/health/db
```

---

**Status:** ✅ Ready for launch  
**Confidence:** HIGH  
**Good luck! 🚀**
