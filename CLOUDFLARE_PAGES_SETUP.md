# Cloudflare Pages Setup Guide - Frontend Deployment

Complete guide to deploy your Intentional Social frontend to Cloudflare Pages.

---

## 📋 Prerequisites

Before starting, ensure you have:

- [ ] Cloudflare account (free tier works) - [Sign up](https://dash.cloudflare.com/sign-up)
- [ ] GitHub account with your code repository
- [ ] Backend API URL ready (e.g., `https://api.yourdomain.com`)
- [ ] Domain name (optional, but recommended)

---

## 🚀 Step 1: Prepare Your Repository

### 1.1 Verify Frontend Structure

Your frontend should be in the `frontend/` directory with this structure:
```
frontend/
├── src/
├── index.html
├── package.json
├── vite.config.js
└── ...
```

### 1.2 Create `_redirects` File for SPA Routing

Create a `public` directory and add a `_redirects` file for React Router to work properly:

```bash
cd frontend
mkdir -p public
```

Create `frontend/public/_redirects`:
```
/*    /index.html   200
```

This ensures all routes are handled by React Router (required for single-page applications).

### 1.3 Commit and Push to GitHub

```bash
# From project root
git add frontend/public/_redirects
git commit -m "Add Cloudflare Pages redirects for SPA routing"
git push origin main
```

---

## 🌐 Step 2: Set Up Cloudflare Pages

### 2.1 Access Cloudflare Pages

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Log in to your account
3. In the left sidebar, click **"Workers & Pages"**
4. Click **"Create application"**
5. Select **"Pages"** tab
6. Click **"Connect to Git"**

### 2.2 Connect GitHub Repository

1. **Authorize Cloudflare** to access your GitHub account
2. **Select your repository** (the one containing your Social_100 project)
3. Click **"Begin setup"**

---

## ⚙️ Step 3: Configure Build Settings

### 3.1 Project Name

- **Project name**: `intentional-social-frontend` (or your preferred name)

### 3.2 Production Branch

- **Production branch**: `main` (or `master` if that's your default branch)

### 3.3 Build Configuration

**Framework preset**: Select **"Vite"** (or "None" if Vite isn't listed)

**Build settings**:
- **Build command**: `cd frontend && npm install && npm run build`
- **Build output directory**: `frontend/dist`
- **Root directory**: Leave empty (or set to `/` if you want to specify)

**Note**: Cloudflare Pages will automatically detect Vite if you select the Vite preset, but you may need to adjust the build command if your frontend is in a subdirectory.

### 3.4 Environment Variables

Click **"Add variable"** and add:

**Option A: Using a Domain (Recommended)**
| Variable Name | Value | Environment |
|--------------|-------|-------------|
| `VITE_API_URL` | `https://api.intentionalsocial.org` | Production |
| `VITE_API_URL` | `http://localhost:8000` | Preview (optional) |

**Note**: Replace `api.intentionalsocial.org` with your actual backend domain.

**Option B: Using VPS IP Address**
| Variable Name | Value | Environment |
|--------------|-------|-------------|
| `VITE_API_URL` | `http://YOUR_VPS_IP:8000` | Production |
| `VITE_API_URL` | `http://localhost:8000` | Preview (optional) |

**Important**: 
- Replace `YOUR_VPS_IP` with your actual VPS IP address (e.g., `http://123.45.67.89:8000`)
- The `VITE_` prefix is required for Vite to expose the variable to your app
- Add this to **Production** environment (and Preview if you want)

**⚠️ Mixed Content Warning (IP Address Setup)**:
- Cloudflare Pages serves your frontend over **HTTPS**
- If your VPS uses **HTTP** (no SSL), browsers will block API calls due to mixed content security
- **Solutions**:
  1. Set up SSL on your VPS (see VPS_SETUP_GUIDE.md Step 10)
  2. Use a free subdomain service (see below)
  3. For testing only: Configure browser to allow mixed content (not recommended for production)

### 3.5 Advanced Settings (Optional)

**Node version**: `18` or `20` (Cloudflare will auto-detect, but you can specify)

**Build environment variables**: Already set above

---

## 🚀 Step 4: Deploy

### 4.1 Initial Deployment

1. Click **"Save and Deploy"**
2. Cloudflare will:
   - Clone your repository
   - Install dependencies (`npm install`)
   - Run the build command
   - Deploy the built files

### 4.2 Monitor Deployment

You'll see the deployment progress in real-time:
- ✅ Installing dependencies
- ✅ Building application
- ✅ Deploying to Cloudflare's edge network

**First deployment takes 2-5 minutes**

### 4.3 Verify Deployment

Once complete, you'll get a deployment URL like:
```
https://intentional-social-frontend.pages.dev
```

Test it:
1. Open the URL in your browser
2. Verify the app loads
3. Test login/registration
4. Check browser console for any errors

---

## 🔗 Step 5: Backend URL Options

### 5.1 Using VPS IP Address

If you're using your VPS IP address directly:

**Environment Variable**:
```
VITE_API_URL=http://YOUR_VPS_IP:8000
```

**Update Backend CORS** (on your VPS):
```bash
# Edit backend .env
cd ~/intentional-social/backend
nano .env
```

Add your Cloudflare Pages URL to CORS_ORIGINS:
```bash
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,http://YOUR_VPS_IP:8000
```

**⚠️ Important**: 
- Your frontend is on HTTPS (Cloudflare Pages)
- Your backend is on HTTP (VPS IP)
- Browsers will block this due to **mixed content** security policy
- **You need HTTPS on your backend** for this to work in production

### 5.2 Free Subdomain Options (Recommended Alternative)

If you don't have a domain, consider these free options:

**Option 1: DuckDNS** (Free, Easy)
1. Go to [DuckDNS.org](https://www.duckdns.org/)
2. Sign up with GitHub/Google
3. Create a subdomain: `yourname.duckdns.org`
4. Point it to your VPS IP
5. Use: `http://yourname.duckdns.org:8000` as your API URL

**Option 2: No-IP** (Free, with limitations)
1. Go to [No-IP.com](https://www.noip.com/)
2. Create free account
3. Create hostname: `yourname.ddns.net`
4. Point to your VPS IP
5. Use: `http://yourname.ddns.net:8000` as your API URL

**Option 3: Set Up SSL on VPS** (Best for Production)
- Follow VPS_SETUP_GUIDE.md Step 10
- Use Let's Encrypt with your IP or subdomain
- Then use: `https://yourname.duckdns.org:8000`

### 5.3 Set Up Custom Domain (If You Have One)

### 5.4 Add Custom Domain (If You Have One)

1. In your Cloudflare Pages project, go to **"Custom domains"**
2. Click **"Set up a custom domain"**
3. Enter your domain: `app.yourdomain.com` (or `yourdomain.com`)
4. Click **"Continue"**

### 5.5 Configure DNS

Cloudflare will show you DNS records to add:

**If your domain is already on Cloudflare:**
- DNS records are added automatically
- Just wait for propagation (usually instant)

**If your domain is elsewhere:**
- Add a **CNAME** record:
  - **Name**: `app` (or `@` for root domain)
  - **Target**: `intentional-social-frontend.pages.dev`
  - **TTL**: Auto

### 5.6 SSL/TLS

Cloudflare automatically provides:
- ✅ Free SSL certificate
- ✅ HTTPS enabled
- ✅ Automatic certificate renewal

Wait 1-5 minutes for SSL to provision.

---

## 🔄 Step 6: Automatic Deployments

### 6.1 How It Works

Cloudflare Pages automatically deploys:
- ✅ Every push to `main` branch → Production
- ✅ Pull requests → Preview deployments
- ✅ Every commit → New deployment

### 6.2 Preview Deployments

- Each PR gets a unique preview URL
- Test changes before merging
- Preview URLs look like: `https://pr-123-intentional-social-frontend.pages.dev`

---

## 🧪 Step 7: Test Your Deployment

### 7.1 Basic Checks

1. **Homepage loads**: Visit your deployment URL
2. **Login page**: Navigate to `/login`
3. **API connection**: Try logging in (should connect to your backend)
4. **Routing**: Navigate between pages (Feed, My Posts, etc.)

### 7.2 Browser Console

Open browser DevTools (F12) and check:
- ✅ No CORS errors
- ✅ API requests going to correct backend URL
- ✅ No 404 errors for assets

### 7.3 Network Tab

Verify:
- ✅ API calls are going to your backend
- ✅ Images/assets loading correctly
- ✅ No failed requests

---

## 🐛 Troubleshooting

### Issue: Build Fails

**Error**: `npm install` fails or build command fails

**Solutions**:
1. Check Node version in build settings (try 18 or 20)
2. Verify `package.json` is in `frontend/` directory
3. Check build logs for specific errors
4. Ensure all dependencies are in `package.json`

**Common fixes**:
```bash
# Make sure package-lock.json is committed
git add frontend/package-lock.json
git commit -m "Add package-lock.json"
git push
```

### Issue: 404 on Routes

**Error**: Direct URL access to routes (e.g., `/feed`) returns 404

**Solution**: Ensure `public/_redirects` file exists:
```
/*    /index.html   200
```

Then rebuild and redeploy.

### Issue: API Connection Fails

**Error**: Frontend can't connect to backend (CORS or network errors)

**Solutions**:
1. Verify `VITE_API_URL` environment variable is set correctly
2. Check backend CORS settings include your Cloudflare Pages URL
3. Ensure backend is accessible (test with `curl http://YOUR_VPS_IP:8000/health`)

**Update backend CORS**:
In your backend `.env`:
```bash
# For Cloudflare Pages
CORS_ORIGINS=https://intentional-social-frontend.pages.dev

# If using custom domain, add it too
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,https://app.yourdomain.com
```

Then restart backend: `docker compose restart backend`

### Issue: Mixed Content Error (HTTPS/HTTP)

**Error**: `Mixed Content: The page was loaded over HTTPS, but requested an insecure resource`

**Cause**: Frontend is HTTPS (Cloudflare), backend is HTTP (VPS IP)

**Solutions**:
1. **Best**: Set up SSL on your VPS (see VPS_SETUP_GUIDE.md Step 10)
2. **Alternative**: Use a free subdomain with SSL (DuckDNS, No-IP)
3. **Testing only**: Disable mixed content in browser (not for production):
   - Chrome: Settings → Privacy → Site Settings → Insecure content → Allow
   - Firefox: about:config → security.mixed_content.block_active_content = false

**Recommended**: Set up SSL on your VPS for production use.

### Issue: Environment Variables Not Working

**Error**: `VITE_API_URL` is undefined or using default value

**Solutions**:
1. Ensure variable name starts with `VITE_`
2. Rebuild after adding environment variables
3. Check variable is set for **Production** environment
4. Clear browser cache and hard refresh (Ctrl+Shift+R)

### Issue: Assets Not Loading

**Error**: Images, CSS, or JS files return 404

**Solutions**:
1. Verify build output directory is `frontend/dist`
2. Check `vite.config.js` has correct base path
3. Ensure assets are in the `dist` folder after build

### Issue: Slow First Load

**Solution**: This is normal for first deployment. Cloudflare caches assets globally, so subsequent loads are fast.

---

## 📊 Step 8: Monitor and Maintain

### 8.1 View Deployment History

1. Go to your Pages project
2. Click **"Deployments"** tab
3. See all deployments with:
   - Status (Success/Failed)
   - Commit message
   - Deployment time
   - Preview URLs

### 8.2 View Logs

1. Click on any deployment
2. View build logs
3. Check for warnings or errors

### 8.3 Rollback

If a deployment breaks:
1. Go to **"Deployments"**
2. Find the last working deployment
3. Click **"..."** menu → **"Retry deployment"** or **"Rollback to this deployment"**

---

## 🔐 Step 9: Security Best Practices

### 9.1 Environment Variables

- ✅ Never commit `.env` files
- ✅ Use Cloudflare Pages environment variables
- ✅ Use different values for Production vs Preview

### 9.2 CORS Configuration

Ensure your backend only allows your frontend domain:
```bash
# Backend .env
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,https://app.yourdomain.com
```

### 9.3 HTTPS

- ✅ Cloudflare provides free SSL for frontend
- ✅ **Important**: If using VPS IP, you need HTTPS on backend too
- ✅ Set up SSL on VPS (see VPS_SETUP_GUIDE.md) or use free subdomain service
- ✅ Update `VITE_API_URL` to use `https://` for backend when SSL is configured

---

## 📝 Step 10: Update Backend CORS

After deploying frontend, update your backend to allow requests from Cloudflare Pages:

### 10.1 On Your VPS

```bash
# Edit backend .env
cd ~/intentional-social/backend
nano .env
```

### 10.2 Update CORS_ORIGINS

**If using Cloudflare Pages URL:**
```bash
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,http://localhost:5173
```

**If using custom domain:**
```bash
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,https://app.yourdomain.com,http://localhost:5173
```

**If using VPS IP (for testing only):**
```bash
CORS_ORIGINS=https://intentional-social-frontend.pages.dev,http://YOUR_VPS_IP:8000,http://localhost:5173
```

### 10.3 Restart Backend

```bash
cd ~/intentional-social
docker compose restart backend
```

### 10.4 Test CORS

From your browser console on Cloudflare Pages:
```javascript
fetch('http://YOUR_VPS_IP:8000/health')
  .then(r => r.json())
  .then(console.log)
```

If you see CORS errors, verify:
1. CORS_ORIGINS includes your Cloudflare Pages URL
2. Backend was restarted after .env changes
3. Check backend logs: `docker compose logs backend`

---

## 🎯 Quick Reference

### Using VPS IP Address (Quick Setup)

If you're using your VPS IP address directly:

1. **In Cloudflare Pages Environment Variables**:
   ```
   VITE_API_URL = http://YOUR_VPS_IP:8000
   ```
   Replace `YOUR_VPS_IP` with your actual IP (e.g., `123.45.67.89`)

2. **On Your VPS, Update Backend CORS**:
   ```bash
   cd ~/intentional-social/backend
   nano .env
   ```
   Add:
   ```bash
   CORS_ORIGINS=https://intentional-social-frontend.pages.dev,http://localhost:5173
   ```
   Then restart:
   ```bash
   cd ~/intentional-social
   docker compose restart backend
   ```

3. **⚠️ Mixed Content Issue**:
   - Your frontend is HTTPS (Cloudflare)
   - Your backend is HTTP (VPS IP)
   - Browsers will block API calls
   - **Solution**: Set up SSL on VPS (see VPS_SETUP_GUIDE.md) or use free subdomain

---

## 🎯 Quick Reference (Full)

### Build Settings Summary

| Setting | Value |
|---------|-------|
| Framework preset | Vite |
| Build command | `cd frontend && npm install && npm run build` |
| Build output directory | `frontend/dist` |
| Root directory | `/` (or leave empty) |
| Node version | 18 or 20 |

### Environment Variables

**With Domain:**
| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://api.yourdomain.com` |

**With VPS IP:**
| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `http://YOUR_VPS_IP:8000` |

**⚠️ Note**: Using IP with HTTP will cause mixed content issues. Set up SSL for production.

### Important Files

- `frontend/public/_redirects` - Required for SPA routing
- `frontend/package.json` - Dependencies and build scripts
- `frontend/vite.config.js` - Vite configuration

---

## ✅ Deployment Checklist

Before going live:

- [ ] Repository is connected to Cloudflare Pages
- [ ] Build settings configured correctly
- [ ] `VITE_API_URL` environment variable set
- [ ] `public/_redirects` file created
- [ ] First deployment successful
- [ ] Frontend loads and displays correctly
- [ ] Login/registration works
- [ ] API calls connect to backend
- [ ] Backend CORS updated with frontend URL
- [ ] Custom domain configured (if using)
- [ ] SSL certificate active (automatic)
- [ ] Tested on mobile devices (optional)

---

## 🆘 Getting Help

### Cloudflare Support

- **Documentation**: [Cloudflare Pages Docs](https://developers.cloudflare.com/pages/)
- **Community**: [Cloudflare Community](https://community.cloudflare.com/)
- **Status**: [Cloudflare Status](https://www.cloudflarestatus.com/)

### Common Commands

**Check deployment status**:
- View in Cloudflare Dashboard → Pages → Your Project → Deployments

**Trigger manual rebuild**:
- Push a new commit, or
- Go to Deployments → Click "Retry deployment" on latest

**View build logs**:
- Click on any deployment → View build logs

---

## 💰 Cost

**Cloudflare Pages**: 
- ✅ **Free tier**: Unlimited requests, 500 builds/month
- ✅ **Bandwidth**: Unlimited
- ✅ **SSL**: Free
- ✅ **Custom domains**: Free
- ✅ **Preview deployments**: Unlimited

**Perfect for MVP!** No cost for typical usage.

---

## 🎉 Success!

Once deployed, your frontend will be:
- ✅ Live on Cloudflare's global edge network
- ✅ Automatically deployed on every push
- ✅ Fast and reliable worldwide
- ✅ Free SSL certificate
- ✅ Custom domain support

**Your frontend URL**: `https://intentional-social-frontend.pages.dev`

**Next steps**:
1. Test all features end-to-end
2. Share with your users
3. Monitor deployments
4. Enjoy automatic updates! 🚀

---

**Estimated Setup Time**: 15-30 minutes  
**Difficulty**: Easy  
**Cost**: Free

Good luck with your deployment! 🎊

