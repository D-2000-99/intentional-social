# DuckDNS Setup Guide - Quick Reference

Quick guide for setting up DuckDNS with your VPS backend.

---

## ✅ What You've Done

- [x] Created DuckDNS account
- [x] Created subdomain (e.g., `yourname.duckdns.org`)
- [x] Pointed DuckDNS to your VPS IP

---

## 🚀 Next Steps

### Step 1: Update Nginx Configuration

On your VPS:

```bash
# Edit Nginx config
sudo nano /etc/nginx/sites-available/intentional-social
```

Update the `server_name` to include your DuckDNS domain:
```nginx
server {
    listen 80;
    server_name yourname.duckdns.org YOUR_VPS_IP;
    # ... rest of config
}
```

Replace `yourname.duckdns.org` with your actual DuckDNS subdomain.

**Test and reload Nginx:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Test the backend:**
```bash
curl http://yourname.duckdns.org:8000/health
# Or if Nginx is configured: curl http://yourname.duckdns.org/health
```

---

### Step 2: Set Up SSL (HTTPS)

**Install Certbot (if not already installed):**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**Get SSL Certificate:**
```bash
# Replace with your DuckDNS subdomain
sudo certbot --nginx -d yourname.duckdns.org

# Follow the prompts:
# - Enter your email address
# - Agree to terms (Y)
# - Redirect HTTP to HTTPS? (Y - recommended)
```

**Verify SSL:**
```bash
curl https://yourname.duckdns.org/health
# Should return: {"status": "ok"}
```

**Auto-renewal is automatic**, but you can test it:
```bash
sudo certbot renew --dry-run
```

---

### Step 3: Update Backend CORS

On your VPS:

```bash
# Edit backend .env
cd ~/intentional-social/backend
nano .env
```

Update `CORS_ORIGINS`:
```bash
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,https://yourname.duckdns.org,http://localhost:5173
```

**Restart backend:**
```bash
cd ~/intentional-social
docker compose restart backend
```

---

### Step 4: Update Cloudflare Pages Environment Variable

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Navigate to **Workers & Pages** → Your Project
3. Go to **Settings** → **Environment variables**
4. Edit `VITE_API_URL`:
   - **Value**: `https://yourname.duckdns.org` (or `https://yourname.duckdns.org:8000` if not using Nginx)
   - **Environment**: Production
5. Click **Save**
6. **Redeploy** (or push a new commit to trigger rebuild)

---

### Step 5: Test Everything

**1. Test Backend (from your local machine):**
```bash
curl https://yourname.duckdns.org/health
# Should return: {"status": "ok"}
```

**2. Test Frontend:**
- Visit your Cloudflare Pages URL
- Try logging in
- Check browser console for errors

**3. Test API Connection:**
Open browser console on your frontend and run:
```javascript
fetch('https://yourname.duckdns.org/health')
  .then(r => r.json())
  .then(console.log)
```

Should return: `{status: "ok"}`

---

## 🔧 Troubleshooting

### DuckDNS Not Resolving

**Check DNS:**
```bash
nslookup yourname.duckdns.org
# Should return your VPS IP
```

**If not resolving:**
1. Check DuckDNS dashboard - verify IP is correct
2. Wait a few minutes for DNS propagation
3. Try: `ping yourname.duckdns.org` to test

### SSL Certificate Fails

**Error**: `Failed to obtain certificate`

**Solutions:**
1. Ensure DuckDNS is pointing to your VPS IP
2. Check Nginx is running: `sudo systemctl status nginx`
3. Verify port 80 is open: `sudo ufw allow 80/tcp`
4. Check Nginx config: `sudo nginx -t`

### CORS Errors

**Error**: CORS policy blocking requests

**Solutions:**
1. Verify `CORS_ORIGINS` includes your Cloudflare Pages URL
2. Restart backend: `docker compose restart backend`
3. Check backend logs: `docker compose logs backend`

### Mixed Content Errors

**Error**: Mixed content (HTTPS/HTTP)

**Solution**: Ensure you're using `https://` in `VITE_API_URL`, not `http://`

---

## 📝 Quick Reference

### Your URLs

- **Backend**: `https://yourname.duckdns.org`
- **Frontend**: `https://intentional-social-frontend.pages.dev`

### Environment Variables

**Cloudflare Pages:**
```
VITE_API_URL = https://yourname.duckdns.org
```

**Backend .env:**
```
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,https://yourname.duckdns.org,http://localhost:5173
```

### Common Commands

```bash
# Test backend
curl https://yourname.duckdns.org/health

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

- [ ] Nginx configured with DuckDNS domain
- [ ] SSL certificate installed (HTTPS working)
- [ ] Backend CORS updated with Cloudflare Pages URL
- [ ] Cloudflare Pages `VITE_API_URL` set to `https://yourname.duckdns.org`
- [ ] Backend accessible via HTTPS
- [ ] Frontend can connect to backend
- [ ] No CORS errors in browser console
- [ ] Login/registration works end-to-end

---

## 🎉 You're Done!

Your setup should now be:
- ✅ Frontend: HTTPS (Cloudflare Pages)
- ✅ Backend: HTTPS (DuckDNS + Let's Encrypt)
- ✅ No mixed content issues
- ✅ CORS properly configured
- ✅ Ready for production!

---

**Need Help?**
- Check `VPS_SETUP_GUIDE.md` for detailed VPS setup
- Check `CLOUDFLARE_PAGES_SETUP.md` for frontend deployment
- Review troubleshooting sections above

