FROM python:3.12-slim

# Install system dependencies (including git and native canvas build deps for POT server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    git \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libjpeg-dev \
    libpango1.0-dev \
    libgif-dev \
    librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (required for some yt-dlp extractors)
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

# Install Node.js 20 (required for POT server)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Clone bgutil POT server (pinned to commit 9612094 from main, 2026-02-20)
RUN git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /opt/pot-server \
    && cd /opt/pot-server \
    && git checkout 96120947fc91ec712f4800d793307e4ab8baaf7f \
    && cd server \
    && npm ci \
    && npx tsc

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

# Create config directory for cookies
RUN mkdir -p /config

# Expose port
EXPOSE 8080

# Run via startup script (manages POT server + uvicorn)
CMD ["./start.sh"]
