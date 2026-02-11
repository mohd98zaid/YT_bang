# Deploying VideoDownloader Web to Railway

This guide will walk you through deploying your VideoDownloader web application to Railway.

## Prerequisites

- A [Railway account](https://railway.app/) (free tier available)
- Git installed on your computer
- Your application code ready in a Git repository

## Step 1: Prepare Your Code

Your application is already configured for Railway deployment with the following files:

- ✅ `Procfile` - Tells Railway how to start your app
- ✅ `railway.toml` - Railway configuration with health checks
- ✅ `requirements.txt` - All Python dependencies
- ✅ `.gitignore` - Excludes unnecessary files from Git
- ✅ `.env.example` - Template for environment variables

## Step 2: Initialize Git Repository (if not already done)

```bash
# Navigate to your project directory
cd C:\Users\mohd9\OneDrive\Desktop\VideoDownloaderWeb

# Initialize Git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit - VideoDownloader Web"
```

## Step 3: Deploy to Railway

### Option A: Deploy via Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Initialize and deploy:**
   ```bash
   railway init
   railway up
   ```

### Option B: Deploy via Railway Dashboard (Recommended)

1. **Go to [Railway Dashboard](https://railway.app/dashboard)**

2. **Click "New Project"**

3. **Select "Deploy from GitHub repo"**
   - If you haven't connected GitHub, do so now
   - Push your code to a GitHub repository first
   - Select your repository

4. **Railway will auto-detect your app** and start deploying

## Step 4: Configure Environment Variables

After deployment, you need to set environment variables:

1. **In Railway Dashboard**, click on your deployed service

2. **Go to "Variables" tab**

3. **Add the following environment variables:**

   ```
   SECRET_KEY=<generate-a-random-secret-key>
   FLASK_ENV=production
   CORS_ORIGINS=https://your-app.up.railway.app
   DOWNLOAD_PATH=/app/downloads
   CONCURRENT_DOWNLOADS=3
   ```

   > **Important:** Generate a secure random SECRET_KEY. You can use:
   > ```python
   > import secrets
   > print(secrets.token_hex(32))
   > ```

4. **Railway automatically sets `PORT`** - don't add it manually

5. **Click "Save"** - Railway will redeploy with new variables

## Step 5: Update CORS After Deployment

Once deployed, Railway will give you a URL like `https://your-app-name.up.railway.app`

1. Update the `CORS_ORIGINS` environment variable with your actual Railway URL:
   ```
   CORS_ORIGINS=https://your-app-name.up.railway.app
   ```

2. Save - Railway will redeploy

## Step 6: Verify Deployment

1. **Check Health Endpoint:**
   ```
   https://your-app.up.railway.app/api/health
   ```
   Should return:
   ```json
   {
     "status": "healthy",
     "environment": "production",
     "version": "1.0.0"
   }
   ```

2. **Open the App:**
   ```
   https://your-app.up.railway.app
   ```

3. **Test a Download:**
   - Paste a YouTube URL
   - Select quality
   - Start download
   - Verify progress updates work

## Important Notes

### 📁 Ephemeral Storage

> **Warning:** Railway uses ephemeral storage. Downloaded files will be deleted when your service restarts (usually during deployments or maintenance).

If you need persistent storage for downloads, you'll need to integrate cloud storage like:
- AWS S3
- Google Cloud Storage
- Cloudflare R2

### 💾 Database

Currently using SQLite. For production at scale, consider:

1. **Upgrade to Railway PostgreSQL:**
   - In Railway Dashboard, click "New" → "Database" → "Add PostgreSQL"
   - Railway will provide a `DATABASE_URL` environment variable
   - You'll need to modify the database code to use PostgreSQL

### 🔒 Security Best Practices

- ✅ Use a strong, random SECRET_KEY
- ✅ Set CORS_ORIGINS to your specific domain(s)
- ✅ Keep your .env file out of version control
- ✅ Never commit sensitive credentials

## Troubleshooting

### App Won't Start

**Check Railway logs:**
```bash
railway logs
```

Common issues:
- Missing environment variables
- PORT binding issues (make sure you're using `os.getenv('PORT')`)
- Dependency installation failures

### WebSocket Connection Fails

- Ensure your CORS_ORIGINS includes your Railway domain
- Check that eventlet is properly installed
- Verify gunicorn is using `--worker-class eventlet`

### Downloads Fail

- Check if static-ffmpeg installed correctly
- Verify yt-dlp is up to date
- Check Railway logs for specific errors

### Health Check Failing

- Ensure `/api/health` endpoint is accessible
- Check Railway service logs
- Verify the app is binding to `0.0.0.0:$PORT`

## Monitoring

**View logs in real-time:**
```bash
railway logs --follow
```

**Check service metrics:**
- Go to Railway Dashboard → Your Service → Metrics
- Monitor CPU, Memory, Network usage

## Updating Your App

1. Make changes to your code locally
2. Commit changes:
   ```bash
   git add .
   git commit -m "Update: description of changes"
   ```
3. Push to GitHub:
   ```bash
   git push
   ```
4. Railway will automatically detect and redeploy

---

## Need Help?

- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)

## Next Steps

After successful deployment:

1. ✅ Test all features thoroughly
2. ✅ Monitor logs for any errors
3. ✅ Consider adding custom domain
4. ✅ Set up database backups (if using PostgreSQL)
5. ✅ Implement persistent storage for downloads (if needed)
