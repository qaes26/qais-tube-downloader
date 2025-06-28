from flask import Flask, render_template, request, send_file, redirect, url_for, flash, after_this_request
import yt_dlp
import os
import shutil
import tempfile

app = Flask(__name__)
# هذا المفتاح السري يجب أن يكون طويلاً وعشوائيًا جدًا.
# في بيئة الإنتاج، يجب أن لا يكون هنا مباشرة بل يتم جلبه من متغيرات البيئة.
# لكن لغرض هذا المشروع، يمكنك تركه هكذا مؤقتًا.
app.secret_key = 'your_super_long_and_random_secret_key_for_production_1234567890ABCDEFGH'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    video_url = request.form['url']
    
    if not video_url:
        print("خطأ: لم يتم إدخال رابط الفيديو.")
        return redirect(url_for('index'))

    temp_dir_obj = None
    actual_video_path = None

    try:
        # إنشاء مجلد مؤقت داخل دليل العمل الحالي للتطبيق
        # هذا يضمن وجود أذونات الكتابة وتنظيف الملفات بعد الاستخدام.
        temp_dir_obj = tempfile.TemporaryDirectory(dir=os.getcwd())
        temp_download_path = temp_dir_obj.name

        # تهيئة خيارات yt-dlp لتنزيل الفيديو (مع الصوت مدمجًا)
        # %(title)s.%(ext)s هو قالب اسم الملف
        output_template = os.path.join(temp_download_path, '%(title)s.%(ext)s')

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # تفضيل MP4
            'outtmpl': output_template, # قالب مسار الإخراج
            'noplaylist': True,         # لا تنزيل قوائم التشغيل
            'quiet': True,              # إخفاء مخرجات yt-dlp غير الضرورية
            'no_warnings': True,        # إخفاء تحذيرات yt-dlp
            'merge_output_format': 'mp4', # التأكد من دمج الصوت والفيديو في ملف MP4 واحد
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"بدء تنزيل الفيديو من: {video_url}")
            info_dict = ydl.extract_info(video_url, download=True)
            
            # الحصول على المسار الفعلي للملف الذي تم تنزيله بعد الدمج
            actual_video_path = ydl.prepare_filename(info_dict)
            print(f"تم تنزيل الفيديو إلى: {actual_video_path}")

            if not os.path.exists(actual_video_path):
                print(f"خطأ: الملف {actual_video_path} غير موجود بعد التنزيل.")
                return redirect(url_for('index'))

            # استخراج اسم الملف لتنزيله بالمتصفح
            download_name = os.path.basename(actual_video_path)
            print(f"إرسال الملف {download_name} إلى المتصفح.")
            
            # إرسال الملف كملف مرفق (يتم تنزيله مباشرة)
            response = send_file(
                actual_video_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='video/mp4' # نوع MIME لملفات الفيديو MP4
            )

            # تسجيل دالة لحذف الملف المؤقت بعد إرسال الاستجابة بالكامل للمتصفح
            @after_this_request
            def remove_file(response):
                if temp_dir_obj:
                    try:
                        temp_dir_obj.cleanup() # حذف المجلد المؤقت ومحتوياته
                        print(f"تم حذف المجلد المؤقت: {temp_dir_obj.name}")
                    except Exception as e:
                        print(f"خطأ في حذف المجلد المؤقت بعد الطلب: {e}")
                return response
            
            return response

    except yt_dlp.utils.DownloadError as e:
        print(f"خطأ في التنزيل (yt-dlp): {e}")
        # حذف المجلد المؤقت فورًا إذا فشل التنزيل
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
                print(f"تم حذف المجلد المؤقت بعد فشل التنزيل: {temp_dir_obj.name}")
            except Exception as e:
                print(f"خطأ في حذف المجلد المؤقت بعد فشل التنزيل (cleanup): {e}")
        return redirect(url_for('index'))
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
        # حذف المجلد المؤقت فورًا إذا حدث خطأ آخر
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
                print(f"تم حذف المجلد المؤقت بعد خطأ غير متوقع: {temp_dir_obj.name}")
            except Exception as e:
                print(f"خطأ في حذف المجلد المؤقت بعد خطأ غير متوقع (cleanup): {e}")
        return redirect(url_for('index'))

# هذا الجزء مهم جداً: تم حذف if __name__ == '__main__':
# لأن Render يستخدم Gunicorn لتشغيل التطبيق، وليس app.run()