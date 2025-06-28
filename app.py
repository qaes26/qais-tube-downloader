from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import io
from PIL import Image # لاستيراد مكتبة الصور (موجودة لميزة الصور)
from fpdf import FPDF # لاستيراد مكتبة PDF (موجودة لميزة الصور)

# استيرادات جديدة لميزة تحويل Word إلى PDF
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

# ###############################################################
# جزء خاص بالتعامل مع اللغة العربية في PDF
# ###############################################################
# تأكد أن لديك ملف خط عربي يدعم Unicode و Arabic shaping
# مثال: Arial, Traditional Arabic, Amiri, Noto Naskh Arabic
# يجب وضع هذا الخط في نفس مجلد ملف app.py أو في مجلد يمكن الوصول إليه
# مثال: الخط المستخدم هنا هو "arial.ttf". تأكد من وجوده.
try:
    pdfmetrics.registerFont(TTFont('ArabicFont', 'arial.ttf'))
except Exception as e:
    print(f"Warning: Could not load Arabic font 'arial.ttf'. Please ensure it's in the same directory as app.py. Error: {e}")
    # يمكن استخدام خط افتراضي إذا لم يتم تحميل الخط المخصص
    pdfmetrics.registerFont(TTFont('ArabicFont', 'FreeSans.ttf')) # FreeSans هو خط قد يكون موجودًا بشكل افتراضي في بعض الأنظمة
    print("Using FreeSans as fallback font.")

def get_arabic_text_for_pdf(text):
    """يعالج النص العربي ليعرض بشكل صحيح في PDF."""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# ###############################################################

# المسار الرئيسي لعرض الصفحة
@app.route('/')
def index():
    return render_template('index.html')

# مسار تحويل الصور إلى PDF
@app.route('/convert_images_to_pdf', methods=['POST'])
def convert_images_to_pdf():
    if 'images' not in request.files:
        return "الرجاء اختيار صورة واحدة على الأقل.", 400

    images = request.files.getlist('images')
    if not images:
        return "الرجاء اختيار صورة واحدة على الأقل.", 400

    image_files = []
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')
    for img_file in images:
        if img_file.filename.lower().endswith(allowed_extensions):
            image_files.append(img_file)
    
    if not image_files:
        return "الرجاء رفع ملفات صور صالحة (PNG, JPG, JPEG, GIF, BMP, TIFF).", 400

    try:
        pdf = FPDF()
        for img_file in image_files:
            img = Image.open(img_file)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)

            pdf.add_page()
            
            page_width = pdf.w - 2 * pdf.l_margin
            page_height = pdf.h - 2 * pdf.t_margin
            
            img_width, img_height = img.size
            aspect_ratio = img_height / img_width

            new_width = page_width
            new_height = new_width * aspect_ratio
            if new_height > page_height:
                new_height = page_height
                new_width = new_height / aspect_ratio

            x = (pdf.w - new_width) / 2
            y = (pdf.h - new_height) / 2
            
            pdf.image(img_io, x=x, y=y, w=new_width, h=new_height)

        pdf_output = pdf.output(dest='S').encode('latin-1')
        pdf_stream = io.BytesIO(pdf_output)

        return send_file(pdf_stream, as_attachment=True, download_name='converted_images.pdf', mimetype='application/pdf')

    except Exception as e:
        app.logger.error(f"Error during PDF conversion: {e}", exc_info=True)
        return f"حدث خطأ أثناء تحويل الصور إلى PDF: {e}", 500

# مسار تحويل ملفات Word إلى PDF
@app.route('/convert_word_to_pdf', methods=['POST'])
def convert_word_to_pdf():
    if 'word_file' not in request.files:
        return "الرجاء رفع ملف Word.", 400
    
    word_file = request.files['word_file']
    if word_file.filename == '':
        return "الرجاء تحديد ملف Word.", 400
    
    if not word_file.filename.lower().endswith(('.doc', '.docx')):
        return "الرجاء رفع ملف Word بصيغة DOC أو DOCX.", 400

    try:
        # قراءة محتوى ملف Word
        document = Document(word_file)
        
        # إنشاء PDF باستخدام ReportLab
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        # تعريف نمط النص العربي
        # يجب التأكد أن الخط 'ArabicFont' تم تحميله بشكل صحيح في pdfmetrics
        arabic_style = ParagraphStyle(
            'Arabic',
            parent=styles['Normal'],
            fontName='ArabicFont', # استخدم اسم الخط اللي سجلته
            fontSize=12,
            leading=14,
            alignment=TA_RIGHT, # محاذاة لليمين للنص العربي
            rightIndent=0,
            leftIndent=0,
            spaceBefore=6,
            spaceAfter=6,
            wordWrap='LTR', # التعامل مع اتجاه النص
            allowWidows=1,
            allowOrphans=1,
        )

        flowables = []
        for para in document.paragraphs:
            text = get_arabic_text_for_pdf(para.text)
            flowables.append(Paragraph(text, arabic_style))
            flowables.append(Spacer(1, 0.2 * inch)) # مسافة بين الفقرات (بوصة)

        # إنشاء الـ PDF
        doc.build(flowables)
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name='converted_word.pdf', mimetype='application/pdf')

    except Exception as e:
        app.logger.error(f"Error during Word to PDF conversion: {e}", exc_info=True)
        return f"حدث خطأ أثناء تحويل ملف Word إلى PDF: {e}. يرجى المحاولة مرة أخرى أو التأكد من تنسيق الملف.", 500

if __name__ == '__main__':
    # تأكد من أن debug=False عند النشر في بيئة الإنتاج!
    app.run(debug=True)