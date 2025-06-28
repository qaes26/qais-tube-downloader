import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey' # لازم تغير ده لمفتاح سري حقيقي في التطبيقات الكبيرة

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
        # قراءة ملف الوورد
        doc = Document(file)

        # إنشاء ملف PDF في الذاكرة
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # إضافة المحتوى من الوورد إلى الـ PDF
        for paragraph in doc.paragraphs:
            text = paragraph.text
            if text: # تأكد أن الفقرة ليست فارغة
                # يمكنك هنا تحسين التنسيق (حجم الخط، اللون، إلخ)
                # هذا مثال بسيط لإضافة النص
                c.drawString(100, 750, text) # X, Y coordinates
                c.showPage() # ابدأ صفحة جديدة لكل فقرة (يمكن تحسينها لتناسب المحتوى)

        c.save()
        buffer.seek(0)

        # إرسال ملف الـ PDF للمستخدم
        return send_file(buffer, as_attachment=True, download_name=f"{os.path.splitext(file.filename)[0]}.pdf", mimetype='application/pdf')
    else:
        flash('الرجاء رفع ملف بصيغة .docx فقط.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)