import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from docx import Document
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image # استيراد مكتبة Pillow

app = Flask(__name__)
app.secret_key = 'supersecretkey_for_word_to_pdf_converter' # يمكنك تغيير هذا لمفتاح سري أقوى

# سجل الخط العربي (تأكد أن مسار الخط صحيح)
try:
    pdfmetrics.registerFont(TTFont('ArabicFont', 'fonts/arial.ttf'))
    print("Arabic font registered successfully.")
except Exception as e:
    print(f"Error registering font: {e}")

# مسار حفظ الملفات المؤقتة
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# أنواع الملفات المسموح بها للصور
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_image_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert_word', methods=['POST'])
def convert_word_to_pdf():
    if 'word_file' not in request.files:
        flash('لم يتم رفع أي ملف Word!')
        return redirect(url_for('index'))

    file = request.files['word_file']

    if file.filename == '':
        flash('لم يتم اختيار ملف Word!')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.docx'):
        try:
            doc = Document(file)
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.setFont('ArabicFont', 12)

            y_position = 750 

            for paragraph in doc.paragraphs:
                text = paragraph.text
                if text:
                    reshaped_text = arabic_reshaper.reshape(text)
                    bidi_text = get_display(reshaped_text)

                    if y_position < 50:
                        c.showPage()
                        c.setFont('ArabicFont', 12)
                        y_position = 750

                    c.drawString(50, y_position, bidi_text)
                    y_position -= 15

            c.save()
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f"{os.path.splitext(file.filename)[0]}.pdf", mimetype='application/pdf')

        except Exception as e:
            flash(f'حدث خطأ أثناء تحويل Word إلى PDF: {e}')
            return redirect(url_for('index'))
    else:
        flash('الرجاء رفع ملف بصيغة .docx فقط للتحويل من Word.')
        return redirect(url_for('index'))

@app.route('/convert_image', methods=['POST'])
def convert_image_to_pdf():
    if 'image_file' not in request.files:
        flash('لم يتم رفع أي ملف صورة!')
        return redirect(url_for('index'))

    file = request.files['image_file']

    if file.filename == '':
        flash('لم يتم اختيار ملف صورة!')
        return redirect(url_for('index'))

    if file and allowed_image_file(file.filename):
        try:
            # فتح الصورة باستخدام Pillow
            img = Image.open(file)

            # إنشاء ملف PDF في الذاكرة
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4) # استخدام A4 كحجم افتراضي للصفحة

            # حساب الأبعاد لتناسب الصورة في الصفحة
            # الحفاظ على نسبة العرض إلى الارتفاع
            img_width, img_height = img.size
            page_width, page_height = A4

            # حساب المقاسات الجديدة للصورة لتناسب الصفحة مع الحفاظ على الأبعاد
            aspect_ratio = img_width / img_height
            if img_width > page_width or img_height > page_height:
                if aspect_ratio > (page_width / page_height):
                    new_width = page_width
                    new_height = page_width / aspect_ratio
                else:
                    new_height = page_height
                    new_width = page_height * aspect_ratio
            else:
                new_width = img_width
                new_height = img_height

            # وضع الصورة في منتصف الصفحة
            x_offset = (page_width - new_width) / 2
            y_offset = (page_height - new_height) / 2

            # تحويل الصورة إلى RGB إذا لم تكن كذلك (مهم لـ ReportLab)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # حفظ الصورة مؤقتًا كملف JPEG لـ ReportLab
            # ReportLab يتعامل بشكل أفضل مع الصور المحفوظة على القرص
            temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], "temp_image.jpg")
            img.save(temp_image_path, 'JPEG')

            # رسم الصورة على الـ PDF
            c.drawImage(temp_image_path, x_offset, y_offset, width=new_width, height=new_height)
            c.showPage() # إضافة صفحة واحدة لكل صورة

            c.save()
            buffer.seek(0)

            # حذف الملف المؤقت
            os.remove(temp_image_path)

            return send_file(buffer, as_attachment=True, download_name=f"{os.path.splitext(file.filename)[0]}.pdf", mimetype='application/pdf')

        except Exception as e:
            flash(f'حدث خطأ أثناء تحويل الصورة إلى PDF: {e}')
            return redirect(url_for('index'))
    else:
        flash('الرجاء رفع ملف صورة بصيغة PNG, JPG, JPEG, أو GIF فقط للتحويل من صورة.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)