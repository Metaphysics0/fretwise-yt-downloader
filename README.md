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
  R2_PUBLIC_URL="https://pub-xxx.r2.dev"
```

### 3. Deploy

```bash
fly deploy
```

### 4. Upload cookies (optional, for authenticated downloads)

```bash
fly ssh console
# Then copy your cookies.txt to /config/cookies.txt
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY` | API key for authentication |
| `R2_ENDPOINT` | Cloudflare R2 endpoint URL |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_BUCKET_NAME` | R2 bucket name |
| `R2_PUBLIC_URL` | Public URL for R2 bucket |
| `COOKIE_PATH` | Path to cookies.txt (default: /config/cookies.txt) |
| `PROXY_URL` | Optional proxy URL for yt-dlp |
