# FretWise YouTube Audio Extractor

A self-hosted YouTube audio extraction microservice for FretWise. Downloads audio via yt-dlp, uploads to Cloudflare R2, and returns the public URL.

## Architecture

```
FretWise Web App → POST /extract → yt-audio-service → R2 → returns URL
```

## API

### POST /extract

Extract audio from a YouTube video and upload to R2.

```bash
curl -X POST https://fretwise-yt-downloader.fly.dev/extract \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "user_id": "usr_abc123",
    "transcription_id": "txn_xyz789"
  }'
```

Response:
```json
{
  "status": "completed",
  "r2_url": "https://pub-xxx.r2.dev/fretwise/users/usr_abc123/transcriptions/txn_xyz789/audio/youtube.mp3",
  "metadata": {
    "title": "Video Title",
    "duration": 245,
    "channel": "Channel Name",
    "video_id": "dQw4w9WgXcQ"
  }
}
```

### GET /health

Returns service status and yt-dlp version.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEY=test
export R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
export R2_ACCESS_KEY_ID=xxx
export R2_SECRET_ACCESS_KEY=xxx
export R2_BUCKET_NAME=fretwise
export R2_PUBLIC_URL=https://pub-xxx.r2.dev
export SENTRY_DSN=https://<key>@o<org>.ingest.us.sentry.io/<project>

# Run the server
uvicorn app.main:app --reload
```

## Deployment

### 1. Create Fly.io app and volume

```bash
fly apps create fretwise-yt-downloader
fly volumes create yt_cookies --region sjc --size 1
```

### 2. Set secrets

```bash
fly secrets set \
  API_KEY="your-api-key" \
  R2_ENDPOINT="https://xxx.r2.cloudflarestorage.com" \
  R2_ACCESS_KEY_ID="xxx" \
  R2_SECRET_ACCESS_KEY="xxx" \
  R2_BUCKET_NAME="fretwise" \
  R2_PUBLIC_URL="https://pub-xxx.r2.dev" \
  SENTRY_DSN="https://<key>@o<org>.ingest.us.sentry.io/<project>"
```

### 3. Deploy

```bash
fly deploy
```

## Maintenance

### Cookie Management

YouTube requires cookies from a logged-in browser session to avoid bot detection. Cookies may need to be refreshed periodically (every few weeks/months).

#### Initial Setup / Refresh Cookies

1. **Create a dedicated Google account** for this service (recommended for isolation)

2. **Export cookies from your browser:**
   - Install the "Get cookies.txt LOCALLY" browser extension ([Firefox](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/) / [Chrome](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/))
   - Sign into YouTube with the dedicated account
   - Close all other YouTube tabs (important - prevents cookie rotation)
   - Click the extension icon on youtube.com → Export
   - Save as `cookies.txt`

3. **Upload to Fly.io:**
   ```bash
   fly ssh sftp shell --app fretwise-yt-downloader
   ```
   Then in the SFTP shell:
   ```
   put /path/to/cookies.txt /config/cookies.txt
   exit
   ```

4. **Verify cookies are working:**
   ```bash
   fly ssh console --app fretwise-yt-downloader -C "yt-dlp --cookies /config/cookies.txt --list-formats 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
   ```
   You should see audio formats (140, 249, 250, 251) listed. If you only see image formats or get a bot error, the cookies need to be refreshed.

#### Troubleshooting

**"Sign in to confirm you're not a bot" error:**
- Cookies are missing or expired
- Re-export and upload fresh cookies

**"Requested format is not available" error:**
- YouTube's JS challenge solver failed
- Check logs: `fly logs --app fretwise-yt-downloader`
- The service uses `--remote-components ejs:github` to solve JS challenges

**View logs:**
```bash
fly logs --app fretwise-yt-downloader
```

**SSH into the container:**
```bash
fly ssh console --app fretwise-yt-downloader
```

**Test a download manually:**
```bash
fly ssh console --app fretwise-yt-downloader -C "yt-dlp --cookies /config/cookies.txt -x --audio-format mp3 'https://www.youtube.com/watch?v=VIDEO_ID' -o /tmp/test.mp3"
```

### Updating yt-dlp

yt-dlp releases updates frequently to keep up with YouTube changes. To update:

```bash
# Redeploy to get latest yt-dlp from requirements.txt
fly deploy

# Or update requirements.txt to a specific version first:
# yt-dlp==2024.12.01
```

### Redeploying

```bash
fly deploy
```

Note: The `/config` volume persists across deployments, so cookies are preserved.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY` | API key for authentication |
| `R2_ENDPOINT` | Cloudflare R2 endpoint URL |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_BUCKET_NAME` | R2 bucket name |
| `R2_PUBLIC_URL` | Public URL for R2 bucket |
| `SENTRY_DSN` | Optional Sentry DSN for error/log reporting |
| `COOKIE_PATH` | Path to cookies.txt (default: /config/cookies.txt) |
| `PROXY_URL` | Optional proxy URL for yt-dlp |
