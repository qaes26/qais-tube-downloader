from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import yt_dlp
import os
import io
import shutil
from PIL import Image # استيراد مكتبة الصور
from fpdf import FPDF # استيراد مكتبة PDF

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # مهم جداً تغير ده لمفتاح سري خاص بيك

# مسار التنزيل القديم (تم تضمينه هنا للتوضيح)
# (لو المسار ده موجود عندك سيبه زي ما هو، لو لأ انسخه من الكود الأصلي)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['video_url']
        try:
            # مسار مؤقت لحفظ ملفات الفيديو المؤقتة
            temp_dir = 'tmp_downloads'
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'noplaylist': True, # لا تنزل قوائم التشغيل
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                video_filename = ydl.prepare_filename(info_dict)

            flash(f"بدء تنزيل الفيديو: {info_dict.get('title', video_url)}", 'success')
            return send_file(video_filename, as_attachment=True)

        except yt_dlp.utils.DownloadError as e:
            error_message = f"خطأ في التنزيل (yt-dlp): {e}"
            flash(error_message, 'danger')
            # حاول حذف المجلد المؤقت في حالة الفشل
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                flash(f"تم حذف المجلد المؤقت بعد فشل التنزيل: {temp_dir}", 'info')
        except Exception as e:
            error_message = f"حدث خطأ غير متوقع: {e}"
            flash(error_message, 'danger')
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                flash(f"تم حذف المجلد المؤقت بعد فشل التنزيل: {temp_dir}", 'info')
    return render_template('index.html')


# مسار جديد لتحويل الصور إلى PDF
@app.route('/images_to_pdf', methods=['GET', 'POST'])
def images_to_pdf():
    if request.method == 'POST':
        # التأكد من وجود ملفات مرفوعة
        if 'images' not in request.files:
            flash('الرجاء اختيار صورة واحدة على الأقل.', 'danger')
            return redirect(request.url)

        images = request.files.getlist('images')
        if not images:
            flash('الرجاء اختيار صورة واحدة على الأقل.', 'danger')
            return redirect(request.url)

        # فلترة الملفات المرفوعة للتأكد من أنها صور
        image_files = [img for img in images if img.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'))]
        if not image_files:
            flash('الرجاء رفع ملفات صور صالحة (PNG, JPG, JPEG, GIF, BMP, TIFF).', 'danger')
            return redirect(request.url)

        try:
            pdf = FPDF()
            for image_file in image_files:
                # فتح الصورة باستخدام Pillow
                img = Image.open(image_file)
                # تحويل الصورة إلى RGB إذا لم تكن كذلك
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # حفظ الصورة في بايت مؤقت عشان نقدر نضيفها للـ PDF
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG') # حفظ كـ JPEG لتجنب مشاكل الشفافية والضغط
                img_io.seek(0) # ارجع للمبتدأ بتاع البايتات

                # إضافة صفحة جديدة للـ PDF
                pdf.add_page()
                # إضافة الصورة للصفحة
                # تحديد عرض الصورة بناءً على عرض الصفحة مع الحفاظ على الأبعاد
                # A4 size: 210mm x 297mm
                page_width = pdf.w - 2 * pdf.l_margin
                page_height = pdf.h - 2 * pdf.t_margin
                
                # Calculate image dimensions to fit page while maintaining aspect ratio
                img_width, img_height = img.size
                aspect_ratio = img_height / img_width

                if img_width > page_width:
                    new_width = page_width
                    new_height = new_width * aspect_ratio
                elif img_height > page_height:
                    new_height = page_height
                    new_width = new_height / aspect_ratio
                else:
                    new_width = img_width
                    new_height = img_height

                # Center the image on the page
                x = (pdf.w - new_width) / 2
                y = (pdf.h - new_height) / 2
                
                pdf.image(img_io, x=x, y=y, w=new_width, h=new_height)

            # إنشاء ملف PDF في الذاكرة
            pdf_output = pdf.output(dest='S').encode('latin-1')
            pdf_stream = io.BytesIO(pdf_output)

            flash('تم تحويل الصور إلى PDF بنجاح!', 'success')
            return send_file(pdf_stream, as_attachment=True, download_name='converted_images.pdf', mimetype='application/pdf')

        except Exception as e:
            flash(f'حدث خطأ أثناء تحويل الصور إلى PDF: {e}', 'danger')
            app.logger.error(f"PDF Conversion Error: {e}", exc_info=True) # لتسجيل الخطأ في السجلات
    return render_template('images_to_pdf.html') # صفحة لعرض فورم التحويل


if __name__ == '__main__':
    app.run(debug=True)