# Quick Start Deployment Guide

This guide will help you deploy Intentional Social for 10-20 users in the fastest way possible.

## ✅ Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] PostgreSQL database (local or managed)
- [ ] Domain name (optional but recommended)
- [ ] SMTP email credentials (Gmail App Password or SendGrid)
- [ ] Server/VPS or cloud hosting account

## 🚀 Option 1: Render (Easiest - Recommended)

### Step 1: Prepare Repository
1. Push your code to GitHub
2. Ensure all changes are committed

### Step 2: Deploy Backend
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name:** intentional-social-backend
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory:** `backend`

### Step 3: Add PostgreSQL Database
1. Click "New +" → "PostgreSQL"
2. Name it: `intentional-social-db`
3. Note the connection string

### Step 4: Configure Environment Variables
In Render dashboard, add these environment variables:

```bash
DATABASE_URL=<from-postgres-service>
SECRET_KEY=<generate-with: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_CONNECTIONS=100
CORS_ORIGINS=https://your-frontend-url.onrender.com

# Email (Required)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

### Step 5: Deploy Frontend
1. Click "New +" → "Static Site"
2. Connect your GitHub repository
3. Configure:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
4. Add environment variable:
   ```bash
   VITE_API_URL=https://your-backend-url.onrender.com
   ```

### Step 6: Update CORS
Update backend CORS_ORIGINS with your frontend URL:
```bash
CORS_ORIGINS=https://your-frontend-url.onrender.com
```

**Done!** Your app should be live.

---

## 🐳 Option 2: Docker on VPS (More Control)

### Prerequisites
- VPS with Docker installed (DigitalOcean, Linode, etc.)
- Domain name pointing to VPS IP

### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd Social_100
```

### Step 2: Configure Environment
```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your values

# Frontend
cd ../frontend
cp .env.example .env
# Set VITE_API_URL to your backend URL
```

### Step 3: Build and Run
```bash
cd ..
docker-compose up -d
```

### Step 4: Set Up SSL (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com -d app.yourdomain.com
```

### Step 5: Configure Nginx
Create `/etc/nginx/sites-available/intentional-social`:

```nginx
# Backend API
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

# Frontend
server {
    listen 80;
    server_name app.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/intentional-social /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📧 Email Setup (Gmail)

1. Enable 2-Factor Authentication on your Gmail account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Use this password in `SMTP_PASSWORD`

**Note:** Gmail has a 500 emails/day limit. For production, consider SendGrid (free tier: 100/day) or Mailgun.

---

## 🔍 Verify Deployment

1. **Health Check:**
   ```bash
   curl https://api.yourdomain.com/health
   # Should return: {"status": "ok"}
   ```

2. **Test Registration:**
   - Go to your frontend URL
   - Try registering a new user
   - Check email for OTP
   - Complete registration

3. **Test Login:**
   - Login with created account
   - Verify JWT token is received

4. **Test Features:**
   - Create a post
   - Send connection request
   - View feed

---

## 🛠️ Troubleshooting

### Backend won't start
- Check logs: `docker logs <container-name>` or Render logs
- Verify DATABASE_URL is correct
- Check SECRET_KEY is 32+ characters
- Ensure all environment variables are set

### Email not sending
- Verify SMTP credentials in `.env` file
- Check Gmail app password is correct
- Verify SMTP settings: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- Check email service limits (Gmail: 500/day)

### Database connection errors
- Verify DATABASE_URL format: `postgresql://user:pass@host:5432/dbname`
- Check database is running
- Verify network connectivity
- Check firewall rules

### CORS errors
- Verify CORS_ORIGINS includes your frontend URL
- Check for trailing slashes
- Ensure HTTPS is used in production

### Frontend can't connect to API
- Verify VITE_API_URL is set correctly
- Check API is accessible (test with curl)
- Verify CORS is configured
- Check browser console for errors

---

## 📊 Monitoring

### Basic Health Monitoring
Set up a simple uptime check:
- **UptimeRobot** (free): Monitor `/health` endpoint every 5 minutes
- **Pingdom**: Free tier available

### Logs
- **Render:** View logs in dashboard
- **Docker:** `docker logs -f <container-name>`
- **VPS:** Check system logs: `journalctl -u docker`

---

## 🔄 Updates & Maintenance

### Deploy Updates
```bash
# If using Docker
git pull
docker-compose build
docker-compose up -d

# If using Render
# Just push to GitHub - auto-deploys
```

### Database Migrations
```bash
# Docker
docker-compose exec backend alembic upgrade head

# Render
# Run in shell: alembic upgrade head
```

### Backup Database
```bash
# Docker
docker-compose exec db pg_dump -U postgres intentional_social > backup.sql

# Render
# Use Render's built-in backup feature
```

---

## 💰 Cost Breakdown

**Render (Recommended):**
- Web Service: $7/month
- PostgreSQL: $7/month
- Static Site: Free
- **Total: ~$14/month**

**VPS (DigitalOcean):**
- Droplet (2GB): $12/month
- Domain: $1/month (annual)
- **Total: ~$13/month**

**Email:**
- Gmail: Free (500/day limit)
- SendGrid: Free (100/day)
- Mailgun: Free (5,000/month)

---

## ✅ Post-Deployment

After deployment:

1. [ ] Test all features end-to-end
2. [ ] Set up database backups
3. [ ] Configure monitoring alerts
4. [ ] Document your deployment
5. [ ] Share with your 10-20 users!

---

## 🆘 Need Help?

Common issues and solutions are in `PRODUCTION_DEPLOYMENT_PLAN.md`.

For specific errors, check:
- Application logs
- Database logs
- Nginx/Reverse proxy logs
- Browser console (for frontend issues)

---

**Estimated Time:** 2-4 hours for first deployment  
**Difficulty:** Medium (Render) / Advanced (VPS)  
**Cost:** $10-25/month

Good luck! 🚀

