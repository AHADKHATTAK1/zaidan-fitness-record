# Deploy ZAIDAN FITNESS RECORD to Render.com

Render.com is **better than Netlify for Flask apps** - it provides true persistent storage, better database support, and easier configuration.

## Why Render?

✅ **Free Tier Available** - Free PostgreSQL database (90-day limit, then $7/month)
✅ **Persistent Storage** - Your SQLite database won't be lost on redeploy
✅ **Easier Setup** - No serverless function wrappers needed
✅ **Better for Flask** - Designed for full-stack apps
✅ **Auto-Deploy** - Push to GitHub, auto-deploys

## Quick Deploy (5 Minutes)

### Option 1: Deploy from GitHub (Recommended)

1. **Go to Render Dashboard**

   - Visit: https://dashboard.render.com/
   - Sign up with GitHub (free)

2. **Create New Web Service**

   - Click **"New +"** → **"Web Service"**
   - Click **"Connect GitHub"** → Select **zaidan-fitness-record**
   - Or paste: `https://github.com/AHADKHATTAK1/zaidan-fitness-record`

3. **Configure Service**

   - **Name**: `zaidan-fitness-record`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`

4. **Add Environment Variables**
   Click **"Add Environment Variable"** for each:

   ```
   SECRET_KEY = [Generate: python -c "import secrets; print(secrets.token_hex(32))"]
   ADMIN_PASSWORD = admin123
   SMTP_HOST = smtp.gmail.com
   SMTP_PORT = 587
   SMTP_USER = zaidanfitnessgym@gmail.com
   SMTP_PASSWORD = [Your Gmail App Password - see WHATSAPP_EMAIL_SETUP.md]
   BACKUP_TO_EMAIL = True
   WHATSAPP_DEFAULT_COUNTRY_CODE = 92
   ```

5. **Add Disk Storage (Important!)**

   - Scroll to **"Disks"** section
   - Click **"Add Disk"**
   - **Name**: `gym-data`
   - **Mount Path**: `/opt/render/project/src`
   - **Size**: `1 GB` (free)
   - This prevents database loss on redeploys

6. **Deploy**
   - Click **"Create Web Service"**
   - Wait 2-3 minutes for first deploy
   - Your app will be at: `https://zaidan-fitness-record.onrender.com`

### Option 2: One-Click Deploy with render.yaml

1. Push the `render.yaml` file to GitHub (already done)
2. Go to: https://dashboard.render.com/select-repo
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` and creates everything
5. Just add the secret environment variables:
   - `ADMIN_PASSWORD`
   - `SMTP_PASSWORD`
   - `WHATSAPP_TOKEN` (optional)
   - `WHATSAPP_PHONE_NUMBER_ID` (optional)

## Add PostgreSQL Database (Optional but Recommended)

1. In Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. **Name**: `zaidan-fitness-db`
3. **Instance Type**: `Free` (90-day trial, then $7/month)
4. Click **"Create Database"**
5. Copy the **"Internal Database URL"**
6. Add to your web service environment variables:
   ```
   DATABASE_URL = [Paste Internal Database URL]
   ```
7. Your app will auto-use PostgreSQL instead of SQLite

## Auto-Deploy Setup

✅ **Already configured!** Every `git push` to `main` branch will auto-deploy.

To disable: Go to Settings → Build & Deploy → Turn off "Auto-Deploy"

## Important Notes

### First-Time Setup

After deployment completes:

1. Visit: `https://zaidan-fitness-record.onrender.com`
2. Login with: `admin` / `admin123` (or your ADMIN_PASSWORD)
3. **Change password immediately**: Settings → Change Password
4. Complete onboarding modal (upload logo, set currency)

### Free Tier Limitations

- **Spin Down**: App sleeps after 15 minutes of inactivity
- **Cold Start**: First request after sleep takes 30-60 seconds
- **Solution**: Use UptimeRobot (free) to ping every 14 minutes: https://uptimerobot.com

### Upgrade to Paid ($7/month)

For production use, upgrade to **Starter** plan:

- No sleep/spin-down
- Always fast
- 24/7 uptime
- More memory (512 MB)

## Troubleshooting

### "Application Error" on Launch

1. Check Render logs: Dashboard → Your Service → Logs
2. Common issues:
   - Missing `SECRET_KEY` env var
   - Missing `gunicorn` in requirements.txt (already added)
   - Database permission errors

### Database Not Persisting

- Make sure you added the **Disk** in Step 5 above
- Path must be: `/opt/render/project/src`
- This mounts persistent storage for `gym.db`

### Email Not Sending

- Generate Gmail App Password: https://myaccount.google.com/apppasswords
- Must have 2FA enabled on Gmail
- See `WHATSAPP_EMAIL_SETUP.md` for detailed steps

### WhatsApp Not Working

- Optional feature, requires Meta Business account
- See `WHATSAPP_EMAIL_SETUP.md` for setup
- Leave blank to disable

## Compare: Netlify vs Render

| Feature       | Netlify                 | Render               |
| ------------- | ----------------------- | -------------------- |
| Flask Support | ⚠️ Limited (serverless) | ✅ Native            |
| Database      | ❌ No persistence       | ✅ Disk storage      |
| Free Tier     | ✅ Yes                  | ✅ Yes               |
| Cold Start    | ⚠️ Very slow            | ⚠️ Slow (15min idle) |
| Auto-Deploy   | ✅ Yes                  | ✅ Yes               |
| PostgreSQL    | ❌ Need external        | ✅ Built-in          |
| Best For      | Static sites            | Full-stack apps      |

**Recommendation**: Use **Render.com** for this Flask app.

## Next Steps

1. ✅ Deploy to Render (follow steps above)
2. ✅ Setup Gmail App Password (see WHATSAPP_EMAIL_SETUP.md)
3. ✅ Test backup email functionality
4. ⚠️ Optional: Setup WhatsApp Business API
5. ✅ Change default admin password
6. ✅ Upload gym logo in onboarding
7. ✅ Start adding members!

## Support

- Render Docs: https://render.com/docs
- Community: https://community.render.com
- Status: https://status.render.com
