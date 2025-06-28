# استخدم صورة بايثون أساسية معتمدة على Debian Buster (صورة خفيفة ومستقرة)
FROM python:3.9-slim-buster

# قم بتحديث قائمة الحزم وتثبيت LibreOffice وحزمة JRE الافتراضية
# LibreOffice ضروري لعمل docx2pdf
# default-jre (Java Runtime Environment) قد يكون مطلوباً لبعض وظائف LibreOffice الداخلية
# --no-install-recommends يقلل من حجم التثبيت
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# تعيين متغير البيئة لـ LibreOffice (قد يكون مفيداً لـ docx2pdf)
ENV UNO_PATH=/usr/lib/libreoffice/program

# تحديد مجلد العمل داخل حاوية Docker
WORKDIR /app

# نسخ جميع ملفات المشروع إلى مجلد العمل داخل الحاوية
COPY . /app

# تثبيت جميع المكتبات البايثون المذكورة في requirements.txt
# --no-cache-dir لتقليل حجم الصورة النهائية
RUN pip install --no-cache-dir -r requirements.txt

# أمر بدء تشغيل تطبيق Flask باستخدام Gunicorn
# 0.0.0.0:$PORT يجعل التطبيق يستمع على أي واجهة شبكة وعلى المنفذ المحدد من Render.com
CMD exec gunicorn --bind 0.0.0.0:$PORT app:app