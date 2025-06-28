from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import io
from PIL import Image # لاستيراد مكتبة الصور
from fpdf import FPDF # لاستيراد مكتبة PDF (لتحويل الصور)

# استيرادات جديدة لميزة تحويل Word إلى PDF
from docx import Document
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
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
# سنستخدم 'arial.ttf' هنا. تأكد من وجوده.
try:
    # سيتم البحث عن الخط في نفس المجلد الذي يعمل منه التطبيق
    pdfmetrics.registerFont(TTFont('ArabicFont', 'arial.ttf'))
    # يمكنك تسجيل خطوط أخرى إذا لزم الأمر
    # pdfmetrics.registerFont(TTFont('ArabicFontBold', 'arialbd.ttf'))
    print("Arabic font 'arial.ttf' loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load Arabic font 'arial.ttf'. Please ensure it's in the same directory as app.py or provide a full path. Error: {e}")
    # إذا لم يتم تحميل Arial، يمكن استخدام خط بديل قد يكون متوفرًا (قد لا يدعم العربية بشكل مثالي)
    # هذا الخط قد لا يكون موجودًا على Render.com، لذا يفضل تضمين 'arial.ttf' مع ملفات المشروع.
    try:
        pdfmetrics.registerFont(TTFont('ArabicFont', 'FreeSans.ttf'))
        print("Using 'FreeSans.ttf' as fallback font. Please consider adding 'arial.ttf' to your project for better Arabic support.")
    except Exception as fe:
        print(f"Error loading FreeSans fallback font: {fe}")
        # إذا فشل كل شيء، يمكنك استخدام خط ReportLab الافتراضي (قد لا يدعم العربية)
        pdfmetrics.registerFont(TTFont('ArabicFont', 'Helvetica'))
        print("Using 'Helvetica' as a last resort. Arabic text might not display correctly.")


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

# مسار تحويل ملفات Word إلى PDF (تم تفعيله)
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
        
        # DocTemplate هو الأنسب للوثائق المعقدة
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()

        # تعريف نمط النص العربي
        # يجب التأكد أن الخط 'ArabicFont' تم تحميله بشكل صحيح في pdfmetrics
        arabic_style_normal = ParagraphStyle(
            'ArabicNormal',
            parent=styles['Normal'],
            fontName='ArabicFont',
            fontSize=12,
            leading=14, # المسافة بين الأسطر
            alignment=TA_RIGHT,
            rightIndent=0,
            leftIndent=0,
            spaceBefore=6,
            spaceAfter=6,
            wordWrap='LTR', # مهم للتعامل مع اتجاه النص المختلط
            allowWidows=1,
            allowOrphans=1,
        )
        
        # نمط للعنوان
        arabic_style_heading1 = ParagraphStyle(
            'ArabicHeading1',
            parent=styles['h1'],
            fontName='ArabicFont',
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceBefore=12,
            spaceAfter=6,
            wordWrap='LTR',
        )
        
        # يمكنك إضافة أنماط أخرى حسب الحاجة (مثل Bold, Italic)

        flowables = [] # العناصر التي ستضاف إلى الـ PDF

        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue # تخطي الفقرات الفارغة

            # تحديد النمط بناءً على محتوى الفقرة (تبسيط)
            # يمكن تحسين هذا الجزء للتعرف على أنماط Word الفعلية (مثل Heading 1)
            if para.style.name.startswith('Heading 1'):
                style_to_use = arabic_style_heading1
            else:
                style_to_use = arabic_style_normal

            # معالجة النص العربي قبل إضافته للـ PDF
            processed_text = get_arabic_text_for_pdf(text)
            
            flowables.append(Paragraph(processed_text, style_to_use))
            # إضافة مسافة بسيطة بين الفقرات
            # flowables.append(Spacer(1, 0.2 * inch)) # ReportLab يستخدم وحدات قياس مثل inch

        # بناء الـ PDF
        doc.build(flowables)
        buffer.seek(0)

        # إرسال الملف الناتج
        return send_file(buffer, as_attachment=True, download_name='converted_word.pdf', mimetype='application/pdf')

    except Exception as e:
        app.logger.error(f"Error during Word to PDF conversion: {e}", exc_info=True)
        # رسالة خطأ أكثر تفصيلاً للمستخدم
        return f"حدث خطأ أثناء تحويل ملف Word إلى PDF: {e}. يرجى التأكد من أن الملف بصيغة DOCX أو DOC وأنه لا يحتوي على تنسيقات معقدة جداً.", 500

if __name__ == '__main__':
    # تأكد من أن debug=False عند النشر في بيئة الإنتاج!
    app.run(debug=True)