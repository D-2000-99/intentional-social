# Fix Connection Request Issue

## Issues Identified

1. **Database Enum Case Mismatch**: The database enum has uppercase values (`ACCEPTED`) but the code expects lowercase (`accepted`)
2. **Network Error**: Frontend can't reach `/connections/request/{id}` endpoint

## Fix 1: Database Enum Case Mismatch

### Step 1: Run the Migration

SSH into your VPS and run:

```bash
cd ~/intentional-social
docker compose exec backend alembic upgrade head
```

This will apply the new migration `fix_connection_status_enum_case.py` which:
- Converts any uppercase enum values to lowercase
- Recreates the enum type with lowercase values
- Ensures the database matches the Python code

### Step 2: Verify the Fix

After running the migration, test the feed endpoint:

```bash
# Should work without errors
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.intentionalsocial.org/feed/
```

## Fix 2: Network Error for Connection Request

The frontend error shows the request to `https://api.intentionalsocial.org/connections/request/1` is failing. Since login works, the backend is accessible, but this specific endpoint might have issues.

### Step 1: Check Nginx Configuration

SSH into your VPS and verify Nginx is configured correctly:

```bash
sudo nano /etc/nginx/sites-available/intentional-social
```

Ensure it has:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.intentionalsocial.org;

    # SSL configuration (if using HTTPS)
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/api.intentionalsocial.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.intentionalsocial.org/privkey.pem;

    # Increase body size for photo uploads
    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important: Allow all HTTP methods including POST
        proxy_method POST;
        proxy_method GET;
        proxy_method PUT;
        proxy_method DELETE;
        proxy_method OPTIONS;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # CORS headers (if not handled by backend)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
}
```

### Step 2: Test Nginx Configuration

```bash
sudo nginx -t
```

If it passes, reload:

```bash
sudo systemctl reload nginx
```

### Step 3: Test the Endpoint Directly

Test if the endpoint is accessible:

```bash
# Test with curl (replace YOUR_TOKEN with actual token)
curl -X POST https://api.intentionalsocial.org/connections/request/1 \
  -H "Authorization: 
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwiZXhwIjoxNzY0OTM1NjcyfQ.1jtqr_otF-O41JfF6Y7LNpGiZWNXEznqg0kKLO0_MvM" \
  -H "Content-Type: application/json" \
  -v
```

Check the response. If it works with curl but not from the frontend, it's likely a CORS issue.

### Step 4: Verify CORS Configuration

Check your backend `.env` file includes your Cloudflare Pages URL:

```bash
cd ~/intentional-social
cat backend/.env | grep CORS_ORIGINS
```

It should include:
```
CORS_ORIGINS=https://intentional-social.pages.dev,https://intentional-social.pages.dev,https://api.intentionalsocial.org
```

If not, update it:

```bash
nano backend/.env
```

Add or update:
```
CORS_ORIGINS=https://intentional-social.pages.dev,https://intentional-social.pages.dev,https://api.intentionalsocial.org
```

Then restart the backend:

```bash
docker compose restart backend
```

### Step 5: Check Backend Logs

Monitor backend logs while testing:

```bash
docker compose logs -f backend
```

Try clicking the "Send Request" button and see if the request appears in the logs. If it doesn't, the request isn't reaching the backend (Nginx or network issue). If it does, check the error message.

## Step 6: Test from Browser Console

Open browser DevTools (F12) and check:

1. **Network Tab**: Look for the request to `/connections/request/1`
   - Check if it's being sent
   - Check the response status
   - Check for CORS errors

2. **Console Tab**: Look for any JavaScript errors

3. **Application Tab → Storage → Local Storage**: Verify `VITE_API_URL` is set correctly

## Quick Verification Checklist

- [ ] Migration applied successfully (`alembic upgrade head`)
- [ ] Feed endpoint works without enum errors
- [ ] Nginx configuration includes all HTTP methods
- [ ] Nginx reloaded successfully
- [ ] CORS_ORIGINS includes Cloudflare Pages URL
- [ ] Backend restarted after CORS change
- [ ] curl test to `/connections/request/1` works
- [ ] Browser network tab shows request being sent
- [ ] No CORS errors in browser console

## If Still Not Working

1. **Check SSL Certificate**: Ensure SSL is properly configured
   ```bash
   sudo certbot certificates
   ```

2. **Check Firewall**: Ensure port 443 (HTTPS) is open
   ```bash
   sudo ufw status
   ```

3. **Check Docker Network**: Ensure backend container can be reached
   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```

4. **Check DNS**: Verify domain points to correct IP
   ```bash
   dig api.intentionalsocial.org
   ```

## Summary of Changes Made

1. ✅ Created migration `fix_connection_status_enum_case.py` to fix enum case mismatch
2. ✅ Updated `Connection` model to use `native_enum=True` for better compatibility
3. ✅ Improved frontend error handling in `api.js`
4. ✅ Fixed POST requests to send empty body `{}` instead of no body

## Next Steps

1. Run the migration on your VPS
2. Update Nginx configuration if needed
3. Verify CORS settings
4. Test the endpoint
5. Redeploy frontend if needed (the frontend changes are already in the code)
