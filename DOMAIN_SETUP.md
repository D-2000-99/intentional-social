# Domain Setup Guide - intentionalsocial.org

Complete guide for setting up your `intentionalsocial.org` domain with your VPS backend and Cloudflare Pages frontend.

---

## 📋 Overview

Your setup will be:
- **Frontend**: `https://app.intentionalsocial.org` (Cloudflare Pages)
- **Backend API**: `https://api.intentionalsocial.org` (VPS with Nginx)

---

## 🌐 Step 1: Configure DNS Records

### 1.1 Access Your Domain Registrar

Log into your domain registrar (where you bought `intentionalsocial.org`).

### 1.2 Add DNS Records

Add these DNS records:

**For Backend API (VPS):**
- **Type**: `A`
- **Name**: `api` (or `@` if your registrar uses root)
- **Value**: `YOUR_VPS_IP` (your VPS IP address)
- **TTL**: `3600` (or Auto)

**For Frontend (Cloudflare Pages):**
- **Type**: `CNAME`
- **Name**: `app`
- **Value**: `intentional-social-frontend.pages.dev` (your Cloudflare Pages URL)
- **TTL**: `3600` (or Auto)

**Optional - Root Domain:**
- **Type**: `CNAME`
- **Name**: `@` (or root/apex)
- **Value**: `intentional-social-frontend.pages.dev`
- **TTL**: `3600`

**Note**: Some registrars don't allow CNAME on root domain. If that's the case:
- Use `A` record pointing to Cloudflare Pages IP (check Cloudflare Pages docs)
- Or redirect root to `app.intentionalsocial.org`

### 1.3 Wait for DNS Propagation

- Usually takes 5-30 minutes
- Can take up to 48 hours (rare)
- Check with: `nslookup api.intentionalsocial.org`

---

## 🖥️ Step 2: Update VPS Configuration

### 2.1 Update Nginx Configuration

On your VPS:

```bash
sudo nano /etc/nginx/sites-available/intentional-social
```

Update the configuration:

```nginx
# Backend API
server {
    listen 80;
    server_name api.intentionalsocial.org YOUR_VPS_IP;

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
```

**Test and reload:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 2.2 Set Up SSL Certificate

**Install Certbot (if not already installed):**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**Get SSL Certificate:**
```bash
sudo certbot --nginx -d api.intentionalsocial.org

# Follow the prompts:
# - Enter your email address
# - Agree to terms (A)
# - Redirect HTTP to HTTPS? (2 - Yes, recommended)
```

**Verify SSL:**
```bash
curl https://api.intentionalsocial.org/health
# Should return: {"status": "ok"}
```

**Test auto-renewal:**
```bash
sudo certbot renew --dry-run
```

### 2.3 Update Backend CORS

```bash
cd ~/intentional-social/backend
nano .env
```

Update `CORS_ORIGINS`:
```bash
CORS_ORIGINS=https://app.intentionalsocial.org,https://intentional-social-frontend.pages.dev,http://localhost:5173
```

**Restart backend:**
```bash
cd ~/intentional-social
docker compose restart backend
```

---

## ☁️ Step 3: Configure Cloudflare Pages Custom Domain

### 3.1 Add Custom Domain to Cloudflare Pages

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Navigate to **Workers & Pages** → Your Project
3. Go to **Custom domains** tab
4. Click **"Set up a custom domain"**
5. Enter: `app.intentionalsocial.org`
6. Click **"Continue"**

### 3.2 Configure DNS (If Domain is on Cloudflare)

If your domain is managed by Cloudflare:
- DNS records are added automatically
- SSL certificate is provisioned automatically
- Wait 1-5 minutes for setup

### 3.3 Configure DNS (If Domain is Elsewhere)

If your domain is with another registrar:
- Add the CNAME record shown in Cloudflare Pages
- Or follow the instructions provided

### 3.4 Wait for SSL

Cloudflare automatically provides SSL for your custom domain. Wait 1-5 minutes.

**Verify:**
```bash
curl https://app.intentionalsocial.org
# Should return HTML content
```

---

## ⚙️ Step 4: Update Cloudflare Pages Environment Variable

### 4.1 Update VITE_API_URL

1. Go to Cloudflare Dashboard → Your Pages Project
2. Go to **Settings** → **Environment variables**
3. Edit `VITE_API_URL`:
   - **Value**: `https://api.intentionalsocial.org`
   - **Environment**: Production
4. Click **Save**

### 4.2 Trigger Rebuild

Either:
- Push a new commit to trigger automatic rebuild, or
- Go to **Deployments** → Click **"Retry deployment"** on latest deployment

---

## 🧪 Step 5: Test Everything

### 5.1 Test Backend API

```bash
# From your local machine
curl https://api.intentionalsocial.org/health
# Should return: {"status": "ok"}
```

### 5.2 Test Frontend

1. Visit: `https://app.intentionalsocial.org`
2. Verify the app loads
3. Check browser console for errors

### 5.3 Test API Connection

Open browser console on your frontend and run:
```javascript
fetch('https://api.intentionalsocial.org/health')
  .then(r => r.json())
  .then(console.log)
```

Should return: `{status: "ok"}`

### 5.4 Test Full Flow

1. Visit `https://app.intentionalsocial.org`
2. Try registering a new user
3. Check email for OTP
4. Complete registration
5. Login
6. Create a post
7. View feed

---

## 🔧 Troubleshooting

### DNS Not Resolving

**Check DNS:**
```bash
nslookup api.intentionalsocial.org
nslookup app.intentionalsocial.org
```

**If not resolving:**
1. Verify DNS records are correct in your registrar
2. Wait for DNS propagation (can take up to 48 hours)
3. Check TTL settings
4. Try different DNS servers: `nslookup api.intentionalsocial.org 8.8.8.8`

### SSL Certificate Issues

**Error**: Certificate not issued

**Solutions:**
1. Ensure DNS is pointing to your VPS IP
2. Verify port 80 is open: `sudo ufw allow 80/tcp`
3. Check Nginx is running: `sudo systemctl status nginx`
4. Verify Nginx config: `sudo nginx -t`

**Renew certificate manually:**
```bash
sudo certbot renew --force-renewal
```

### CORS Errors

**Error**: CORS policy blocking requests

**Solutions:**
1. Verify `CORS_ORIGINS` includes `https://app.intentionalsocial.org`
2. Restart backend: `docker compose restart backend`
3. Check backend logs: `docker compose logs backend`
4. Verify no typos in domain name

### Frontend Not Loading

**Check:**
1. DNS is resolving: `nslookup app.intentionalsocial.org`
2. SSL certificate is active (check browser for padlock icon)
3. Cloudflare Pages deployment is successful
4. Environment variable `VITE_API_URL` is set correctly

---

## 📝 Quick Reference

### Your URLs

- **Frontend**: `https://app.intentionalsocial.org`
- **Backend API**: `https://api.intentionalsocial.org`
- **Cloudflare Pages (fallback)**: `https://intentional-social-frontend.pages.dev`

### DNS Records Summary

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| A | `api` | `YOUR_VPS_IP` | Backend API |
| CNAME | `app` | `intentional-social-frontend.pages.dev` | Frontend |

### Environment Variables

**Cloudflare Pages:**
```
VITE_API_URL = https://api.intentionalsocial.org
```

**Backend .env:**
```
CORS_ORIGINS=https://app.intentionalsocial.org,https://intentional-social-frontend.pages.dev,http://localhost:5173
```

### Common Commands

```bash
# Test backend
curl https://api.intentionalsocial.org/health

# Test frontend
curl https://app.intentionalsocial.org

# Check DNS
nslookup api.intentionalsocial.org
nslookup app.intentionalsocial.org

# Check Nginx status
sudo systemctl status nginx

# Restart backend
cd ~/intentional-social && docker compose restart backend

# View backend logs
docker compose logs -f backend

# Test SSL renewal
sudo certbot renew --dry-run
```

---

## ✅ Checklist

- [ ] DNS records added (A record for api, CNAME for app)
- [ ] DNS propagated (verified with nslookup)
- [ ] Nginx configured with `api.intentionalsocial.org`
- [ ] SSL certificate installed for backend
- [ ] Backend accessible via `https://api.intentionalsocial.org`
- [ ] Backend CORS updated with frontend domain
- [ ] Cloudflare Pages custom domain configured
- [ ] Cloudflare Pages SSL active
- [ ] `VITE_API_URL` updated to `https://api.intentionalsocial.org`
- [ ] Frontend accessible via `https://app.intentionalsocial.org`
- [ ] Frontend can connect to backend (no CORS errors)
- [ ] Full user flow tested (register, login, post)

---

## 🎉 Optional: Root Domain Setup

If you want `intentionalsocial.org` (without subdomain) to work:

### Option 1: Redirect to App Subdomain

Add to your registrar or Cloudflare:
- **Type**: `A` record
- **Name**: `@`
- **Value**: Cloudflare Pages IP (check Cloudflare docs)
- Or use redirect service

### Option 2: Use Cloudflare Pages for Root

1. In Cloudflare Pages, add custom domain: `intentionalsocial.org`
2. Follow DNS instructions provided
3. Both `intentionalsocial.org` and `app.intentionalsocial.org` will work

---

## 🎊 You're Done!

Your production setup:
- ✅ Professional domain name
- ✅ HTTPS everywhere (frontend and backend)
- ✅ No mixed content issues
- ✅ Proper DNS configuration
- ✅ SSL certificates active
- ✅ Ready for users!

**Your live URLs:**
- Frontend: `https://app.intentionalsocial.org`
- Backend: `https://api.intentionalsocial.org`

---

**Need Help?**
- Check `VPS_SETUP_GUIDE.md` for detailed VPS setup
- Check `CLOUDFLARE_PAGES_SETUP.md` for frontend deployment
- Review troubleshooting sections above

