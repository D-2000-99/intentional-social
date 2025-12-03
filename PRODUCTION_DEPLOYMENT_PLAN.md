# Production Deployment Plan - Intentional Social

**Target:** 10-20 users  
**Timeline:** 1-2 weeks  
**Status:** ✅ **VIABLE** - Application is functionally complete and ready for small-scale deployment

---

## 🎯 Executive Summary

**Yes, this is viable for 10-20 users!** The application is functionally complete with:
- ✅ Authentication & authorization (JWT)
- ✅ Email verification
- ✅ Connection system (100 limit enforced)
- ✅ Posts & chronological feed
- ✅ Tag system
- ✅ Modern tech stack (FastAPI + React)

**Estimated Cost:** $10-25/month (VPS + domain)  
**Estimated Setup Time:** 8-16 hours  
**Recommended Platform:** DigitalOcean, Linode, or Render

---

## 📊 Production Readiness Assessment

### ✅ Ready for Production
- [x] Core features implemented
- [x] Database migrations (Alembic)
- [x] Environment-based configuration
- [x] JWT authentication
- [x] Password hashing (bcrypt)
- [x] CORS configuration
- [x] Email verification system
- [x] API structure

### ⚠️ Critical Issues to Address (Before Launch)

1. **Database Migration** (HIGH PRIORITY)
   - Currently using SQLite (`test.db`) in development
   - Must migrate to PostgreSQL for production
   - **Impact:** Data loss risk, performance issues
   - **Effort:** 2-3 hours

2. **Rate Limiting** (HIGH PRIORITY)
   - No rate limiting on auth endpoints
   - **Risk:** Brute force attacks, spam registrations
   - **Effort:** 4-6 hours

3. **Security Headers** (MEDIUM PRIORITY)
   - Missing security headers (HSTS, CSP, etc.)
   - **Risk:** XSS vulnerabilities
   - **Effort:** 2-3 hours

4. **Environment Variables** (MEDIUM PRIORITY)
   - No `.env.example` files
   - **Risk:** Configuration errors
   - **Effort:** 1 hour

5. **SSL/HTTPS** (HIGH PRIORITY)
   - Required for production
   - **Effort:** 1-2 hours (automated with Let's Encrypt)

6. **Database Backups** (HIGH PRIORITY)
   - No backup strategy
   - **Risk:** Data loss
   - **Effort:** 2-3 hours

7. **Monitoring & Logging** (MEDIUM PRIORITY)
   - Basic logging exists, but no monitoring
   - **Effort:** 3-4 hours

---

## 🚀 Deployment Plan: Phase-by-Phase

### Phase 1: Pre-Deployment Hardening (Week 1, Days 1-3)

#### Day 1: Security & Configuration

**1.1 Add Rate Limiting**
```bash
cd backend
pip install slowapi
```

**Files to modify:**
- `backend/app/main.py` - Add rate limiter
- `backend/app/routers/auth.py` - Add rate limits to endpoints
- `backend/requirements.txt` - Add slowapi

**Rate limit recommendations:**
- Login: 5 attempts/minute
- Registration: 3 attempts/hour
- OTP requests: 3 attempts/hour
- General API: 100 requests/minute

**1.2 Create Environment Variable Templates**
- Create `backend/.env.example`
- Create `frontend/.env.example`
- Document all required variables

**1.3 Add Security Headers**
- Install `python-multipart` if not present
- Add security middleware to FastAPI

#### Day 2: Database Migration

**2.1 Set Up PostgreSQL**
- Choose managed database (DigitalOcean, AWS RDS) or self-hosted
- Create production database
- Test connection

**2.2 Migration Script**
- Create migration guide
- Test migrations on staging database
- Document rollback procedure

**2.3 Database Connection Pooling**
- Configure SQLAlchemy connection pool
- Set appropriate pool size for 10-20 users (5-10 connections)

#### Day 3: Docker & Containerization

**3.1 Create Dockerfile for Backend**
- Multi-stage build
- Python 3.13 base image
- Install dependencies
- Expose port 8000

**3.2 Create Dockerfile for Frontend**
- Node.js build stage
- Nginx serve stage
- Production-optimized build

**3.3 Create docker-compose.yml**
- Backend service
- Frontend service
- PostgreSQL service (optional, or use managed DB)
- Environment variables
- Volume mounts

**3.4 Test Locally**
- Build and run containers
- Verify all services communicate
- Test database migrations in container

---

### Phase 2: Infrastructure Setup (Week 1, Days 4-5)

#### Day 4: Server Setup

**4.1 Choose Hosting Provider**
**Recommended options:**

**Option A: DigitalOcean Droplet** ($12-24/month)
- 2GB RAM, 1 vCPU (sufficient for 10-20 users)
- Full control, good for learning
- Manual setup required

**Option B: Render** ($7-25/month)
- Managed PostgreSQL included
- Automatic SSL
- Easy deployment from Git
- Less control, easier setup

**Option C: Fly.io** ($5-15/month)
- Good for small apps
- Global edge network
- Easy scaling

**Recommendation:** Start with **Render** for simplicity, migrate to VPS later if needed.

**4.2 Server Configuration (if using VPS)**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**4.3 Domain Setup**
- Purchase domain (Namecheap, Google Domains, etc.)
- Point DNS to server IP (or Render/Fly.io)
- Set up subdomains:
  - `api.yourdomain.com` → Backend
  - `app.yourdomain.com` → Frontend
  - Or use single domain with path routing

#### Day 5: SSL & Reverse Proxy

**5.1 Set Up Nginx (if using VPS)**
- Install Nginx
- Configure reverse proxy
- Set up SSL with Let's Encrypt (Certbot)

**5.2 SSL Configuration**
```nginx
# /etc/nginx/sites-available/intentional-social
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**5.3 Certbot Setup**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com -d app.yourdomain.com
```

---

### Phase 3: Deployment (Week 2, Days 1-2)

#### Day 1: Backend Deployment

**1.1 Environment Variables**
Create `.env` on server:
```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=<generate-32-char-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_CONNECTIONS=100
CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com

# Email (required for registration)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

**1.2 Database Setup**
```bash
# Run migrations
cd backend
alembic upgrade head

# Optional: Seed initial data
python seed.py
```

**1.3 Deploy Backend**
- If using Docker: `docker-compose up -d`
- If using Render/Fly.io: Connect GitHub repo, set env vars, deploy

**1.4 Test Backend**
```bash
curl https://api.yourdomain.com/health
# Should return: {"status": "ok"}
```

#### Day 2: Frontend Deployment

**2.1 Build Frontend**
```bash
cd frontend
npm install
npm run build
```

**2.2 Environment Variables**
Create `.env.production`:
```bash
VITE_API_URL=https://api.yourdomain.com
```

**2.3 Deploy Frontend**
- If using Docker: Serve with Nginx
- If using Render: Deploy as static site
- If using VPS: Copy `dist/` to Nginx web root

**2.4 Test Full Stack**
- Register new user
- Verify email works
- Test connection requests
- Create posts
- View feed

---

### Phase 4: Post-Deployment (Week 2, Days 3-5)

#### Day 3: Monitoring & Logging

**3.1 Set Up Logging**
- Configure structured logging
- Set up log rotation
- Monitor error rates

**3.2 Basic Monitoring**
**Free options:**
- **UptimeRobot** - Monitor API health (free tier: 50 monitors)
- **Sentry** - Error tracking (free tier: 5k events/month)
- **Simple health check endpoint** - Already exists at `/health`

**3.3 Database Monitoring**
- Monitor connection pool usage
- Set up slow query logging
- Track database size

#### Day 4: Backup Strategy

**4.1 Database Backups**
```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL > backup_$DATE.sql

# Add to crontab (daily at 2 AM)
0 2 * * * /path/to/backup-script.sh
```

**4.2 Backup Storage**
- Upload to S3/Backblaze (free tier available)
- Or store on separate server
- Keep 7 daily, 4 weekly backups

**4.3 Test Restore**
- Practice restoring from backup
- Document restore procedure

#### Day 5: Documentation & Handoff

**5.1 Create Runbook**
- How to restart services
- How to check logs
- How to run migrations
- How to restore backups
- Emergency contacts

**5.2 User Documentation**
- How to register
- How connections work
- How to use tags
- FAQ

**5.3 Performance Baseline**
- Document current response times
- Set up alerts for degradation
- Plan scaling strategy if needed

---

## 📋 Detailed Implementation Checklist

### Critical (Must Do Before Launch)

- [ ] **Rate Limiting**
  - [ ] Install slowapi
  - [ ] Add to auth endpoints
  - [ ] Add to registration/OTP endpoints
  - [ ] Test rate limits

- [ ] **PostgreSQL Migration**
  - [ ] Set up production PostgreSQL database
  - [ ] Update DATABASE_URL
  - [ ] Run migrations
  - [ ] Test connection
  - [ ] Verify data integrity

- [ ] **Environment Variables**
  - [ ] Create backend/.env.example
  - [ ] Create frontend/.env.example
  - [ ] Document all variables
  - [ ] Set production values

- [ ] **SSL/HTTPS**
  - [ ] Obtain SSL certificate
  - [ ] Configure Nginx/reverse proxy
  - [ ] Test HTTPS endpoints
  - [ ] Force HTTPS redirects

- [ ] **CORS Configuration**
  - [ ] Update CORS_ORIGINS with production URLs
  - [ ] Test cross-origin requests
  - [ ] Remove localhost from production

- [ ] **Email Configuration**
  - [ ] Set up SMTP credentials
  - [ ] Test email sending
  - [ ] Verify OTP delivery
  - [ ] Set up email monitoring

- [ ] **Database Backups**
  - [ ] Create backup script
  - [ ] Schedule automated backups
  - [ ] Test restore procedure
  - [ ] Set up backup storage

### Important (Should Do Soon)

- [ ] **Security Headers**
  - [ ] Add security middleware
  - [ ] Configure CSP headers
  - [ ] Add HSTS headers
  - [ ] Test security headers

- [ ] **Docker Setup**
  - [ ] Create backend Dockerfile
  - [ ] Create frontend Dockerfile
  - [ ] Create docker-compose.yml
  - [ ] Test container builds

- [ ] **Monitoring**
  - [ ] Set up uptime monitoring
  - [ ] Configure error tracking
  - [ ] Set up log aggregation
  - [ ] Create alerting rules

- [ ] **Performance Optimization**
  - [ ] Review N+1 queries (already identified in NEXT_STEPS.md)
  - [ ] Add database indexes
  - [ ] Optimize feed queries
  - [ ] Test with realistic data

### Nice to Have (Can Do Later)

- [ ] **CI/CD Pipeline**
  - [ ] Set up GitHub Actions
  - [ ] Automated testing
  - [ ] Automated deployment
  - [ ] Rollback procedure

- [ ] **Advanced Monitoring**
  - [ ] Application performance monitoring (APM)
  - [ ] Database query monitoring
  - [ ] User analytics (privacy-first)

- [ ] **Documentation**
  - [ ] API documentation (OpenAPI)
  - [ ] Deployment guide
  - [ ] Troubleshooting guide
  - [ ] User guide

---

## 🛠️ Required Code Changes

### 1. Add Rate Limiting

**backend/requirements.txt:**
```python
slowapi==0.1.9
```

**backend/app/main.py:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**backend/app/routers/auth.py:**
```python
from slowapi import Limiter
from app.main import app

limiter = Limiter(app.state.limiter)

@router.post("/login")
@limiter.limit("5/minute")
def login(...):
    ...

@router.post("/register")
@limiter.limit("3/hour")
def register(...):
    ...

@router.post("/send-registration-otp")
@limiter.limit("3/hour")
def send_registration_otp(...):
    ...
```

### 2. Add Security Headers

**backend/requirements.txt:**
```python
secure==0.3.0
```

**backend/app/main.py:**
```python
from secure import SecureHeaders

secure_headers = SecureHeaders()

@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.framework.fastapi(response)
    return response
```

### 3. Environment Variable Templates

**backend/.env.example:**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Security
SECRET_KEY=your-32-character-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application
MAX_CONNECTIONS=100
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Email (Required for registration)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

**frontend/.env.example:**
```bash
VITE_API_URL=http://localhost:8000
```

### 4. Database Connection Pooling

**backend/app/db.py:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
```

---

## 🐳 Docker Configuration

### backend/Dockerfile
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### frontend/Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### frontend/nginx.conf
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### docker-compose.yml (root directory)
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      - db
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-intentional_social}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 💰 Cost Estimates

### Option 1: VPS (DigitalOcean/Linode)
- **VPS:** $12-24/month (2GB RAM, 1 vCPU)
- **Domain:** $10-15/year
- **Email (SendGrid):** Free tier (100 emails/day)
- **Backups (Backblaze B2):** Free tier (10GB)
- **Total:** ~$15-25/month

### Option 2: Managed Platform (Render)
- **Web Service:** $7/month (starter)
- **PostgreSQL:** $7/month (starter)
- **Static Site:** Free
- **Domain:** $10-15/year
- **Total:** ~$15/month

### Option 3: Fly.io
- **App Hosting:** $5-10/month
- **PostgreSQL:** $3-5/month (small)
- **Domain:** $10-15/year
- **Total:** ~$10-18/month

**Recommendation:** Start with Render or Fly.io for simplicity, migrate to VPS if you need more control.

---

## 🔒 Security Checklist

Before going live, verify:

- [ ] All passwords are hashed (bcrypt) ✅
- [ ] JWT tokens expire (60 minutes) ✅
- [ ] Rate limiting on auth endpoints
- [ ] HTTPS enforced
- [ ] CORS properly configured
- [ ] SQL injection prevention (using ORM) ✅
- [ ] XSS prevention (React escapes by default) ✅
- [ ] Security headers set
- [ ] Secrets in environment variables ✅
- [ ] Database credentials secured
- [ ] Email credentials secured
- [ ] Error messages don't leak sensitive info
- [ ] Input validation on all endpoints ✅

---

## 📈 Scaling Considerations (Future)

For 10-20 users, current setup is sufficient. When scaling:

**50-100 users:**
- Add Redis for caching
- Optimize database queries (N+1 fixes)
- Add CDN for static assets
- Consider read replicas

**100+ users:**
- Load balancing
- Database connection pooling optimization
- Background job queue (Celery)
- Advanced monitoring (Prometheus, Grafana)

---

## 🚨 Emergency Procedures

### Service Down
1. Check server status: `docker ps` or Render dashboard
2. Check logs: `docker logs <container>` or Render logs
3. Restart services: `docker-compose restart` or Render redeploy
4. Check database: `psql $DATABASE_URL -c "SELECT 1"`

### Database Issues
1. Check connection: Test DATABASE_URL
2. Check disk space: `df -h`
3. Check database size: `SELECT pg_size_pretty(pg_database_size('dbname'));`
4. Restore from backup if needed

### Email Not Working
1. Check SMTP credentials in `.env` file
2. Verify SMTP settings: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
3. Check email service limits (Gmail: 500/day)
4. Consider switching to SendGrid/Mailgun for production

---

## 📞 Support & Maintenance

### Daily Checks (5 minutes)
- [ ] Health endpoint: `curl https://api.yourdomain.com/health`
- [ ] Check error logs
- [ ] Monitor disk space

### Weekly Tasks (30 minutes)
- [ ] Review error logs
- [ ] Check backup status
- [ ] Review user registrations
- [ ] Check database size

### Monthly Tasks (1 hour)
- [ ] Update dependencies
- [ ] Review security patches
- [ ] Test backup restore
- [ ] Review performance metrics

---

## ✅ Success Criteria

You're ready for production when:

1. ✅ All critical checklist items completed
2. ✅ Health endpoint returns 200
3. ✅ User registration works end-to-end
4. ✅ Email verification delivers
5. ✅ Database backups running
6. ✅ SSL certificate valid
7. ✅ Monitoring alerts configured
8. ✅ Documentation complete

---

## 🎯 Next Steps (Immediate Action)

1. **Today:**
   - Review this plan
   - Choose hosting provider
   - Set up rate limiting
   - Create .env.example files

2. **This Week:**
   - Set up PostgreSQL database
   - Create Docker configuration
   - Deploy to staging environment
   - Test all features

3. **Next Week:**
   - Deploy to production
   - Set up monitoring
   - Configure backups
   - Onboard first users

---

**Estimated Total Time:** 16-24 hours of focused work  
**Estimated Cost:** $10-25/month  
**Risk Level:** Low (small user base, can iterate quickly)

Good luck with your deployment! 🚀

