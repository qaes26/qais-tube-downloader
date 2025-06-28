from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import io
from PIL import Image
from fpdf import FPDF # لاستيراد مكتبة PDF (لتحويل الصور) - تأكد إنها fpdf2 إذا مثبتة

# استيرادات جديدة ومعدلة لميزة تحويل Word إلى PDF
from docx2pdf import convert
import tempfile # لاستخدام ملفات مؤقتة

app = Flask(__name__)

# ###############################################################
# جزء خاص بالتعامل مع اللغة العربية في PDF (لم يعد ضرورياً لتحويل Word)
# ###############################################################
# ملاحظة: هذا الجزء لم يعد مطلوباً لتحويل Word إلى PDF إذا استخدمت docx2pdf،
# لأن LibreOffice سيتولى عملية التصيير (Rendering) بما في ذلك الخطوط العربية.
# لكنه ما زال ضرورياً لوظائف أخرى قد تضيفها مستقبلاً أو إذا كانت fpdf تستخدمه.
# لأجل هذا التطبيق، سأبقيه معلقاً جزئياً لتوضيح أنه لم يعد يستخدم مباشرة لتحويل Word.

# تأكد أن لديك ملف خط عربي يدعم Unicode و Arabic shaping
# سنبقي تسجيل الخط هنا فقط في حال كانت FPDF تستخدمه في وظائف أخرى
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    # سيتم البحث عن الخط في نفس المجلد الذي يعمل منه التطبيق
    pdfmetrics.registerFont(TTFont('ArabicFont', 'arial.ttf'))
    print("Arabic font 'arial.ttf' loaded successfully for general PDF use.")
except Exception as e:
    print(f"Warning: Could not load Arabic font 'arial.ttf' for general PDF use. Error: {e}")
    # إذا لم يتم تحميل Arial، يمكن استخدام خط بديل قد يكون متوفرًا
    try:
        pdfmetrics.registerFont(TTFont('ArabicFont', 'FreeSans.ttf'))
        print("Using 'FreeSans.ttf' as fallback font for general PDF use. Please consider adding 'arial.ttf' to your project for better Arabic support.")
    except Exception as fe:
        print(f"Error loading FreeSans fallback font: {fe}")
        pdfmetrics.registerFont(TTFont('ArabicFont', 'Helvetica'))
        print("Using 'Helvetica' as a last resort for general PDF use. Arabic text might not display correctly.")

# هذه الدالة لم تعد تستخدم مباشرة في تحويل Word إذا استخدمت docx2pdf
# لكنها قد تكون مفيدة لوظائف أخرى تستخدم reportlab
# def get_arabic_text_for_pdf(text):
#     """يعالج النص العربي ليعرض بشكل صحيح في PDF."""
#     import arabic_reshaper
#     from bidi.algorithm import get_display
#     reshaped_text = arabic_reshaper.reshape(text)
#     bidi_text = get_display(reshaped_text)
#     return bidi_text
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

        pdf_output = pdf.output(dest='S')
        pdf_stream = io.BytesIO(pdf_output)

        return send_file(pdf_stream, as_attachment=True, download_name='converted_images.pdf', mimetype='application/pdf')

    except Exception as e:
        app.logger.error(f"Error during PDF conversion: {e}", exc_info=True)
        return f"حدث خطأ أثناء تحويل الصور إلى PDF: {e}", 500

# مسار تحويل ملفات Word إلى PDF (تم تفعيله باستخدام docx2pdf)
@app.route('/convert_word_to_pdf', methods=['POST'])
def convert_word_to_pdf():
    if 'word_file' not in request.files:
        return "الرجاء رفع ملف Word.", 400
    
    word_file = request.files['word_file']
    if word_file.filename == '':
        return "الرجاء تحديد ملف Word.", 400
    
    # docx2pdf يدعم .doc و .docx، لكن .doc قد يتطلب تثبيت خاص على بعض الأنظمة
    if not word_file.filename.lower().endswith(('.doc', '.docx')):
        return "الرجاء رفع ملف Word بصيغة DOC أو DOCX.", 400

    try:
        # حفظ الملف المؤقت لـ Word لأن docx2pdf يحتاج مسار ملف
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_word_file:
            word_file.save(temp_word_file.name)
            temp_word_path = temp_word_file.name
        
        # تحديد مسار ملف PDF الناتج المؤقت
        temp_pdf_path = temp_word_path.replace(".docx", ".pdf").replace(".doc", ".pdf")

        try:
            # استخدام docx2pdf للتحويل
            # هذا السطر هو الأهم والذي يتطلب وجود LibreOffice أو MS Word
            convert(temp_word_path, temp_pdf_path)

            # قراءة ملف PDF الناتج وإرساله
            with open(temp_pdf_path, 'rb') as f:
                pdf_output_stream = io.BytesIO(f.read())
            
            return send_file(pdf_output_stream, as_attachment=True, download_name='converted_word.pdf', mimetype='application/pdf')

        finally:
            # تنظيف الملفات المؤقتة
            os.unlink(temp_word_path)
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)

    except Exception as e:
        app.logger.error(f"Error during Word to PDF conversion with docx2pdf: {e}", exc_info=True)
        return f"حدث خطأ أثناء تحويل ملف Word إلى PDF: {e}. يرجى التأكد من أن الخادم يدعم تحويل DOCX (يتطلب LibreOffice/MS Word).", 500

if __name__ == '__main__':
    # تأكد من أن debug=False عند النشر في بيئة الإنتاج!
    app.run(debug=True)