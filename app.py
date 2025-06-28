import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)
app.secret_key = 'supersecretkey_for_word_to_pdf_converter' # يمكنك تغيير هذا لمفتاح سري أقوى

# سجل الخط العربي (تأكد أن مسار الخط صحيح)
# تأكد أن ملف arial.ttf موجود داخل مجلد "fonts" في مجلد المشروع
try:
    pdfmetrics.registerFont(TTFont('ArabicFont', 'fonts/arial.ttf'))
    print("Arabic font registered successfully.")
except Exception as e:
    print(f"Error registering font: {e}")
    # يمكنك إضافة طريقة للتعامل مع هذا الخطأ بشكل أفضل إذا لم يتم تسجيل الخط

# مسار حفظ الملفات المؤقتة
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_word_to_pdf():
    if 'word_file' not in request.files:
        flash('لم يتم رفع أي ملف!')
        return redirect(url_for('index'))

    file = request.files['word_file']

    if file.filename == '':
        flash('لم يتم اختيار ملف!')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.docx'):
        try:
            # قراءة ملف الوورد
            doc = Document(file)

            # إنشاء ملف PDF في الذاكرة
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)

            # تحديد الخط العربي وحجمه
            c.setFont('ArabicFont', 12) 

            # إحداثي Y الأولي لبدء الكتابة من أعلى الصفحة
            y_position = 750 # يمكنك تعديل هذا الهامش العلوي

            for paragraph in doc.paragraphs:
                text = paragraph.text
                if text:
                    # معالجة النص العربي لكي يظهر بشكل صحيح (الشكل والاتجاه)
                    # يقوم arabic_reshaper بتشكيل الحروف
                    reshaped_text = arabic_reshaper.reshape(text)
                    # يقوم python-bidi بتصحيح اتجاه النص من اليمين لليسار
                    bidi_text = get_display(reshaped_text)

                    # التأكد من أن النص لن يخرج عن حدود الصفحة
                    # (قد تحتاج لتعديل هذا بناء على حجم الخط وطول النص)
                    if y_position < 50: # إذا اقتربنا من الهامش السفلي
                        c.showPage() # ابدأ صفحة جديدة
                        c.setFont('ArabicFont', 12) # أعد تعيين الخط للصفحة الجديدة
                        y_position = 750 # ارجع لأعلى الصفحة الجديدة

                    # رسم النص على الـ PDF
                    # X coordinate (الموضع الأفقي): يمكن تعديله للهوامش أو المحاذاة
                    # هنا 50 هو هامش من اليسار، يمكنك تعديله ليناسب المحاذاة لليمين للنص العربي
                    c.drawString(50, y_position, bidi_text)

                    # تحريك الموضع لأسفل للفقرة التالية
                    y_position -= 15 # مسافة بين السطور، يمكنك تعديلها

            c.save()
            buffer.seek(0)

            # إرسال ملف الـ PDF للمستخدم
            return send_file(buffer, as_attachment=True, download_name=f"{os.path.splitext(file.filename)[0]}.pdf", mimetype='application/pdf')

        except Exception as e:
            flash(f'حدث خطأ أثناء التحويل: {e}')
            return redirect(url_for('index'))
    else:
        flash('الرجاء رفع ملف بصيغة .docx فقط.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)