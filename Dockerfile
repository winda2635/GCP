FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    gnupg \
    xvfb \
    xauth \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Official Google Chrome, matching the original bot's channel='chrome' behavior.
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm -f google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the system libraries Playwright/Chromium may need.
RUN python -m playwright install-deps

COPY gcp.py .

# The original bot uses headless=False. Xvfb supplies the virtual display on Railway.
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac & export DISPLAY=:99; exec python gcp.py"]
