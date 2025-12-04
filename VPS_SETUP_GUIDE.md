# VPS Setup & Backend Deployment Guide

Complete step-by-step guide to set up a VPS and deploy the Intentional Social backend.

> **Note:** This guide deploys **backend and database only**. The frontend should be deployed separately (e.g., Netlify, Vercel, or another server). The docker-compose.yml file only includes backend and PostgreSQL services.

---

## 📋 Prerequisites

Before starting, you'll need:
- [ ] A VPS account (DigitalOcean, Linode, AWS EC2, etc.)
- [ ] SSH access to your VPS
- [ ] Domain name (optional but recommended)
- [ ] Your code pushed to GitHub (or another Git repository)

---

## Part 1: VPS Setup

### Step 1: Choose & Create VPS

**Recommended Providers:**
- **DigitalOcean**: $12/month (2GB RAM, 1 vCPU) - [Sign up](https://www.digitalocean.com)
- **Linode**: $12/month (2GB RAM, 1 vCPU) - [Sign up](https://www.linode.com)
- **Vultr**: $12/month (2GB RAM, 1 vCPU) - [Sign up](https://www.vultr.com)
- **AWS EC2**: t3.micro (Free tier eligible) - [Sign up](https://aws.amazon.com)

**Recommended Configuration:**
- **OS**: Ubuntu 22.04 LTS (or 24.04 LTS)
- **RAM**: 2GB minimum
- **CPU**: 1 vCPU minimum
- **Storage**: 25GB minimum
- **Region**: Choose closest to your users

**Create VPS:**
1. Sign up for your chosen provider
2. Create a new droplet/server/instance
3. Select Ubuntu 22.04 LTS
4. Choose the $12/month plan (2GB RAM)
5. Choose a datacenter region
6. Add your SSH key (or set a root password)
7. Click "Create" / "Launch"

**Note your VPS IP address** - you'll need it!

---

### Step 2: Initial Server Configuration

**Connect to your VPS:**
```bash
# If you have SSH key
ssh root@YOUR_VPS_IP

# Or if using password
ssh root@YOUR_VPS_IP
# Enter password when prompted
```

**Update system:**
```bash
# Update package list
apt update

# Upgrade all packages
apt upgrade -y

# Install essential tools
apt install -y curl wget git vim ufw
```

**Create a non-root user (recommended):**
```bash
# Create new user
adduser deploy
# Enter password when prompted (or press Enter to skip)

# Add user to sudo group
usermod -aG sudo deploy

# Switch to new user
su - deploy
```

**Set up firewall:**
```bash
# Allow SSH (port 22)
sudo ufw allow 22/tcp

# Allow HTTP (port 80)
sudo ufw allow 80/tcp

# Allow HTTPS (port 443)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

### Step 3: Install Docker & Docker Compose

**Install Docker:**
```bash
# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
exit
# Then SSH back in
ssh deploy@YOUR_VPS_IP

# Verify Docker installation
docker --version
# Should show: Docker version 24.x.x or similar
```

**Install Docker Compose:**
```bash
# Download latest Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
# Should show: Docker Compose version v2.x.x
```

---

## Part 2: Upload & Deploy Backend

### Step 4: Clone Your Repository

**Option A: Using Git (Recommended)**

```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Or if using SSH
git clone git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git

# Navigate to project
cd YOUR_REPO_NAME
# Or if your repo is named Social_100:
cd Social_100
```

**Option B: Upload Files Manually**

If you don't have Git set up, you can use SCP:

```bash
# From your local machine
scp -r /path/to/Social_100 deploy@YOUR_VPS_IP:~/
```

Or use SFTP client like FileZilla, WinSCP, or VS Code's Remote-SSH extension.

---

### Step 5: Set Up Backend Environment

**Navigate to backend directory:**
```bash
cd ~/Social_100/backend
# Or wherever your project is located
```

**Create `.env` file:**
```bash
# Create .env file
nano .env
# Or use vim: vim .env
```

**Add the following content (replace with your actual values):**

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@db:5432/intentional_social

# Security
SECRET_KEY=YOUR_32_CHARACTER_SECRET_KEY_HERE_GENERATE_ONE
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application Settings
MAX_CONNECTIONS=100
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://app.yourdomain.com

# Email Configuration (Required for registration)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# S3 Configuration (for photo uploads)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_PHOTO_PREFIX=posts/photos
S3_PRESIGNED_URL_EXPIRATION=3600
```

**Generate SECRET_KEY:**
```bash
# On your VPS, run:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the output and paste it as SECRET_KEY in .env
```

**Save and exit:**
- In `nano`: Press `Ctrl+X`, then `Y`, then `Enter`
- In `vim`: Press `Esc`, type `:wq`, then `Enter`

**Set proper permissions:**
```bash
# Make .env readable only by you
chmod 600 .env
```

---

### Step 6: Configure Docker Compose

**Edit docker-compose.yml (if needed):**

The existing `docker-compose.yml` should work, but verify it's configured correctly:

```bash
cd ~/Social_100
cat docker-compose.yml
```

**If you need to modify it**, edit with:
```bash
nano docker-compose.yml
```

**Key things to check:**
- Backend service uses `./backend/.env` file
- Database password matches your `.env` file
- Port 8000 is mapped for backend (frontend is deployed separately)

---

### Step 7: Deploy with Docker Compose

**Build and start services:**
```bash
cd ~/Social_100

# Build and start all services in detached mode
docker-compose up -d --build

# Watch logs (optional)
docker-compose logs -f

# Check if containers are running
docker-compose ps
```

**Expected output:**
```
NAME                STATUS
social_100_backend_1   Up
social_100_db_1        Up
```

**Note:** Frontend is not included in this docker-compose. Deploy frontend separately (e.g., Netlify, Vercel, or another server).

**Check backend logs:**
```bash
# View backend logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend
```

**Test backend:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Should return: {"status": "ok"}
```

---

## Part 3: Set Up Reverse Proxy & SSL

### Step 8: Install Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Start Nginx
sudo systemctl start nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

**Test Nginx:**
```bash
curl http://localhost
# Should return HTML content
```

---

### Step 9: Configure Nginx Reverse Proxy

**Create Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/intentional-social
```

**Add this configuration:**

```nginx
# Backend API
server {
    listen 80;
    server_name api.yourdomain.com YOUR_VPS_IP;

    # Increase body size for photo uploads
    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Frontend (if deploying frontend on same server)
# Uncomment and configure if you're hosting frontend on this VPS
# server {
#     listen 80;
#     server_name app.yourdomain.com;
#
#     location / {
#         proxy_pass http://localhost:80;
#         proxy_set_header Host $host;
#     }
# }
```

**Replace `yourdomain.com` with your actual domain**, or use your VPS IP for testing.

**Enable the site:**
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/intentional-social /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
```

**Test the reverse proxy:**
```bash
# From your local machine or VPS
curl http://YOUR_VPS_IP/health
# Should return: {"status": "ok"}
```

---

### Step 10: Set Up SSL with Let's Encrypt

**Install Certbot:**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**Get SSL Certificate:**

**If you have a domain:**
```bash
# Replace with your actual domain (only backend API)
sudo certbot --nginx -d api.yourdomain.com

# If you're also hosting frontend on this server, add it:
# sudo certbot --nginx -d api.yourdomain.com -d app.yourdomain.com

# Follow the prompts:
# - Enter your email
# - Agree to terms
# - Choose whether to redirect HTTP to HTTPS (recommended: Yes)
```

**If you don't have a domain:**
- You can use the VPS IP, but SSL won't work (certificates require domain names)
- For production, you should get a domain ($10-15/year from Namecheap, Google Domains, etc.)

**Auto-renewal (already set up by Certbot):**
```bash
# Test renewal
sudo certbot renew --dry-run
```

**Verify SSL:**
```bash
# Test HTTPS endpoint
curl https://api.yourdomain.com/health
# Should return: {"status": "ok"}
```

---

## Part 4: Domain Configuration (Optional)

### Step 11: Point Domain to VPS

**If you have a domain:**

1. **Get your VPS IP address:**
   ```bash
   # On your VPS
   curl ifconfig.me
   # Or check in your VPS provider dashboard
   ```

2. **Configure DNS:**
   - Log into your domain registrar (Namecheap, GoDaddy, etc.)
   - Go to DNS settings
   - Add/Edit A records:
     - `api.yourdomain.com` → `YOUR_VPS_IP`
     - `app.yourdomain.com` → `YOUR_VPS_IP`
   - Save changes

3. **Wait for DNS propagation** (5 minutes to 48 hours, usually 15-30 minutes)

4. **Test DNS:**
   ```bash
   # From your local machine
   nslookup api.yourdomain.com
   # Should return your VPS IP
   ```

---

## Part 5: Verify Deployment

### Step 12: Test Everything

**1. Test Backend Health:**
```bash
curl https://api.yourdomain.com/health
# Or if no domain: curl http://YOUR_VPS_IP/health
# Should return: {"status": "ok"}
```

**2. Test API Endpoints:**
```bash
# Test registration OTP endpoint
curl -X POST https://api.yourdomain.com/auth/send-registration-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Should return: {"detail": "Verification code sent to your email"}
```

**3. Check Logs:**
```bash
# Backend logs
docker-compose logs backend

# Database logs
docker-compose logs db

# All logs
docker-compose logs
```

**4. Check Container Status:**
```bash
docker-compose ps
# All should show "Up"
```

---

## Part 6: Maintenance & Updates

### Updating Your Backend

**When you make code changes:**

```bash
# SSH into your VPS
ssh deploy@YOUR_VPS_IP

# Navigate to project
cd ~/Social_100

# Pull latest code
git pull

# Rebuild and restart containers
docker-compose up -d --build

# Check logs
docker-compose logs -f backend
```

### Running Database Migrations

**If you add new migrations:**
```bash
# Migrations run automatically on container start
# But you can also run manually:
docker-compose exec backend alembic upgrade head
```

### Viewing Logs

```bash
# All logs
docker-compose logs

# Backend only
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart just backend
docker-compose restart backend

# Stop all services
docker-compose down

# Start all services
docker-compose up -d
```

### Backup Database

```bash
# Create backup
docker-compose exec db pg_dump -U postgres intentional_social > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T db psql -U postgres intentional_social < backup_20241203.sql
```

---

## Troubleshooting

### Backend Won't Start

**Check logs:**
```bash
docker-compose logs backend
```

**Common issues:**
- **Database connection error**: Check `DATABASE_URL` in `.env`
- **Port already in use**: Check if port 8000 is free: `sudo lsof -i :8000`
- **Missing environment variables**: Verify all required vars in `.env`

### Database Connection Issues

```bash
# Test database connection
docker-compose exec db psql -U postgres -c "SELECT 1;"

# Check database is running
docker-compose ps db
```

### Nginx 502 Bad Gateway

**Check:**
1. Backend is running: `docker-compose ps backend`
2. Backend is accessible: `curl http://localhost:8000/health`
3. Nginx config is correct: `sudo nginx -t`

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Check Nginx SSL config
sudo nginx -t
```

### Can't Access from Browser

**Check firewall:**
```bash
sudo ufw status
# Should show ports 80 and 443 as ALLOW
```

**Check Nginx:**
```bash
sudo systemctl status nginx
```

**Check Docker:**
```bash
docker-compose ps
# All containers should be "Up"
```

---

## Security Checklist

Before going live, ensure:

- [ ] Firewall is enabled (`sudo ufw status`)
- [ ] SSH key authentication is set up (disable password auth)
- [ ] `.env` file has secure permissions (`chmod 600 .env`)
- [ ] SSL certificate is installed and working
- [ ] Database password is strong
- [ ] SECRET_KEY is 32+ characters and random
- [ ] CORS_ORIGINS only includes your frontend domain
- [ ] Regular backups are scheduled

---

## Quick Reference Commands

```bash
# View all running containers
docker-compose ps

# View logs
docker-compose logs -f backend

# Restart backend
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build

# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Check Nginx status
sudo systemctl status nginx

# Reload Nginx config
sudo systemctl reload nginx

# Test Nginx config
sudo nginx -t

# View backend logs
docker-compose logs backend | tail -50
```

---

## Next Steps

1. **Deploy Frontend**: See frontend deployment guide
2. **Set Up Monitoring**: Configure UptimeRobot or similar
3. **Set Up Backups**: Schedule automated database backups
4. **Configure Email**: Set up Gmail App Password or SendGrid
5. **Test End-to-End**: Register user, create post, test all features

---

## Support

If you encounter issues:

1. Check logs: `docker-compose logs backend`
2. Check Nginx: `sudo nginx -t` and `sudo systemctl status nginx`
3. Verify environment variables in `.env`
4. Test database connection
5. Check firewall rules

---

**Estimated Setup Time:** 1-2 hours  
**Difficulty:** Intermediate  
**Cost:** $12-24/month (VPS) + $10-15/year (domain)

Good luck! 🚀

