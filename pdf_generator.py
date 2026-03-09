import os
import io
import logging
import base64
import json
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from datetime import datetime
from collections import defaultdict

from database import SessionLocal, Project, Analysis, BOQItem, Defect, UploadedFile, SiteVisit, SiteVisitImage

logger = logging.getLogger("pdf_generator")

FONT_PATH = "fonts/Amiri-Regular.ttf"
FONT_NAME = "Amiri"
try:
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    else:
        logger.warning("Font file not found, falling back to Helvetica.")
        FONT_NAME = "Helvetica"
except Exception as e:
    logger.error(f"Error loading font: {e}")
    FONT_NAME = "Helvetica"

def clean_text_for_pdf(text):
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "💰": "اقتصادي",
        "🪶": "خفيف",
        "🛡️": "آمن",
        "🔴": "عالية",
        "🟡": "متوسطة",
        "🟢": "منخفضة",
        "✅": "تم الحل",
        "⏳": "مفتوح",
        "📊": "نتائج",
        "⚠️": "تحذير",
    }
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
    return text

def draw_arabic_text(c, text, x, y, font_size=12):
    try:
        cleaned_text = clean_text_for_pdf(text)
        reshaped_text = arabic_reshaper.reshape(cleaned_text)
        bidi_text = get_display(reshaped_text)
        c.setFont(FONT_NAME, font_size)
        c.drawString(x, y, bidi_text)
    except Exception as e:
        c.setFont("Helvetica", font_size)
        c.drawString(x, y, text)

def generate_project_report(project_id):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        analyses = db.query(Analysis).filter(Analysis.project_id == project_id).order_by(Analysis.created_at.desc()).all()
        boqs = db.query(BOQItem).filter(BOQItem.project_id == project_id).all()
        defects = db.query(Defect).filter(Defect.project_id == project_id).all()
        site_visits = db.query(SiteVisit).filter(SiteVisit.project_id == project_id).order_by(SiteVisit.visit_date.desc()).limit(5).all()

        filename = f"report_{project_id}.pdf"
        c = canvas.Canvas(filename, pagesize=A4)
        w, h = A4

        draw_arabic_text(c, f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 50, h - 20, 10)

        draw_arabic_text(c, f"تقرير مشروع: {project.name}", 50, h - 50, 24)
        draw_arabic_text(c, f"الموقع: {project.location}", 50, h - 80, 12)
        c.line(50, h - 90, w - 50, h - 90)

        y = h - 120

        # التحليلات
        draw_arabic_text(c, "التحليلات الهندسية الهامة", 50, y, 16)
        y -= 30

        important_analyses = [a for a in analyses if a.task_type != "chat"][:10]

        for ana in important_analyses:
            if y < 100:
                c.showPage()
                y = h - 50
                draw_arabic_text(c, "التحليلات الهندسية الهامة (تابع)", 50, y, 16)
                y -= 30

            draw_arabic_text(c, f"- {ana.task_type}: {ana.input_text[:50]}...", 50, y, 12)
            y -= 20

            res_data = ana.result_json.get("results", {}) if ana.result_json else {}
            text_content = res_data.get("📊 النتائج", "") or res_data.get("📄 تحليل الملف", "")
            if text_content:
                short_text = str(text_content).replace("**", "")[:100]
                draw_arabic_text(c, short_text, 70, y, 10)
                y -= 20

            img_data = res_data.get("image_data")
            if img_data:
                try:
                    img_bytes = base64.b64decode(img_data)
                    img = ImageReader(io.BytesIO(img_bytes))
                    if y - 120 < 50:
                        c.showPage()
                        y = h - 50
                    c.drawImage(img, 50, y - 120, width=150, height=100, preserveAspectRatio=True)
                    y -= 140
                except:
                    pass
            y -= 10

        chat_count = len([a for a in analyses if a.task_type == "chat"])
        if chat_count > 0:
            draw_arabic_text(c, f"(تم تجاهل {chat_count} محادثة عادية)", 70, y, 10)
            y -= 20

        # العيوب
        if y < 150:
            c.showPage()
            y = h - 50
            draw_arabic_text(c, "العيوب المسجلة", 50, y, 16)
            y -= 30
        else:
            y -= 20
            draw_arabic_text(c, "العيوب المسجلة", 50, y, 16)
            y -= 30

        for defect in defects:
            if y < 100:
                c.showPage()
                y = h - 50
                draw_arabic_text(c, "العيوب المسجلة (تابع)", 50, y, 16)
                y -= 30
            line = f"- {defect.description} | {defect.severity} | {defect.status}"
            draw_arabic_text(c, line, 50, y, 10)
            y -= 20
            if defect.image_id:
                img_file = db.query(UploadedFile).filter(UploadedFile.id == defect.image_id).first()
                if img_file and os.path.exists(img_file.file_path):
                    try:
                        c.drawImage(img_file.file_path, 50, y-80, width=100, height=80, preserveAspectRatio=True)
                        y -= 100
                    except:
                        pass
            y -= 10

        # زيارات الموقع
        if y < 150:
            c.showPage()
            y = h - 50
            draw_arabic_text(c, "آخر زيارات الموقع", 50, y, 16)
            y -= 30
        else:
            y -= 20
            draw_arabic_text(c, "آخر زيارات الموقع", 50, y, 16)
            y -= 30

        for visit in site_visits:
            if y < 100:
                c.showPage()
                y = h - 50
                draw_arabic_text(c, "آخر زيارات الموقع (تابع)", 50, y, 16)
                y -= 30
            line = f"- {visit.visit_date.strftime('%Y-%m-%d')}: {visit.location_name or 'بدون موقع'}"
            draw_arabic_text(c, line, 50, y, 10)
            y -= 20
            first_img = db.query(SiteVisitImage).filter(SiteVisitImage.site_visit_id == visit.id).first()
            if first_img and os.path.exists(first_img.image_path):
                try:
                    c.drawImage(first_img.image_path, 50, y-80, width=120, height=80, preserveAspectRatio=True)
                    y -= 100
                except:
                    pass
            y -= 10

        # BOQ
        if y < 150:
            c.showPage()
            y = h - 50
            draw_arabic_text(c, "جدول الكميات (BOQ)", 50, y, 16)
            y -= 30
        else:
            y -= 20
            draw_arabic_text(c, "جدول الكميات (BOQ)", 50, y, 16)
            y -= 30

        grouped_items = defaultdict(lambda: {"quantity": 0, "total_price": 0, "unit": ""})
        for item in boqs:
            key = item.description
            grouped_items[key]["quantity"] += item.quantity
            grouped_items[key]["total_price"] += item.total_price
            grouped_items[key]["unit"] = item.unit

        total_cost = 0
        for desc, values in grouped_items.items():
            price = values["total_price"]
            total_cost += price
            line = f"{desc} | {values['quantity']} {values['unit']} | {price} جنيه"
            draw_arabic_text(c, line, 50, y, 10)
            y -= 20

        y -= 10
        draw_arabic_text(c, f"الإجمالي التقديري: {total_cost} جنيه", 50, y, 14)

        c.save()
        with open(filename, "rb") as f:
            pdf_bytes = f.read()
        os.remove(filename)
        return pdf_bytes

    except Exception as e:
        logger.error(f"PDF Gen Error: {e}")
        return None
    finally:
        db.close()
