FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# تثبيت Python + Xvfb + المتطلبات الأساسية
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    ca-certificates \
    gnupg \
    xvfb \
    xauth \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# تثبيت Google Chrome Stable
# gcp.py يستخدم channel='chrome'
# ==========================================
RUN wget -q -O /tmp/google-chrome-key.pub \
    https://dl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor \
    -o /usr/share/keyrings/google-chrome.gpg \
    /tmp/google-chrome-key.pub \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    /tmp/google-chrome-key.pub

# إنشاء بيئة Python افتراضية
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# تثبيت مكتبات المشروع
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# تثبيت متطلبات Playwright
RUN python -m playwright install-deps

# تثبيت Chromium الخاص بـ Playwright
RUN python -m playwright install chromium

# نسخ البوت
COPY gcp.py .

# تشغيل Xvfb ثم البوت
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac & export DISPLAY=:99; exec python gcp.py"]
