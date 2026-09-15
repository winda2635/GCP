# استخدم صورة Playwright الرسمية التي تحتوي على Chromium وكل التبعيات
FROM mcr.microsoft.com/playwright:v1.48.0-noble

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كود البوت
COPY bot.py .

# إنشاء مجلد لبروفايل المتصفح (سيتم استخدام /tmp إذا لم يتم تركيب Volume)
RUN mkdir -p /tmp/browser_profile

# تعيين متغير البيئة للبروفايل
ENV BROWSER_PROFILE_DIR=/tmp/browser_profile

# تشغيل البوت
CMD ["python", "bot.py"]