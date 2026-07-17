FROM node:22-bookworm-slim AS pot-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    build-essential \
    python3 \
    pkg-config \
    libcairo2-dev \
    libjpeg-dev \
    libpango1.0-dev \
    libgif-dev \
    librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch 1.3.1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /opt/pot-server \
    && cd /opt/pot-server/server \
    && npm ci \
    && npx tsc \
    && npm prune --omit=dev


FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    libcairo2 \
    libjpeg62-turbo \
    libpango-1.0-0 \
    libgif7 \
    librsvg2-2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=pot-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=pot-builder /opt/pot-server/server/build /opt/pot-server/server/build
COPY --from=pot-builder /opt/pot-server/server/node_modules /opt/pot-server/server/node_modules
COPY --from=pot-builder /opt/pot-server/server/package.json /opt/pot-server/server/package.json

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tests/ ./tests/
COPY start.sh .
RUN python -m unittest discover -s tests \
    && rm -rf tests \
    && chmod +x start.sh \
    && mkdir -p /config

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8080/ready || exit 1

CMD ["./start.sh"]
