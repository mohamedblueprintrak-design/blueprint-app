import os
import io
import logging
import base64
from datetime import datetime
from collections import defaultdict

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

from database import SessionLocal, Project, Analysis, BOQItem, Defect, UploadedFile, SiteVisit, SiteVisitImage, Task

logger = logging.getLogger("pdf_generator")

FONT_PATH_REGULAR = "fonts/Amiri-Regular.ttf"
FONT_PATH_BOLD = "fonts/Amiri-Bold.ttf"  # اختياري – إذا لم يوجد سيتم استخدام العادي
FONT_NAME = "Amiri"

try:
    if os.path.exists(FONT_PATH_REGULAR):
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH_REGULAR))
        logger.info("تم تسجيل الخط العادي بنجاح")
    else:
        logger.warning("ملف الخط العادي غير موجود، سيتم استخدام Helvetica.")
        FONT_NAME = "Helvetica"

    # تسجيل الخط العريض إذا وجد
    if os.path.exists(FONT_PATH_BOLD):
        pdfmetrics.registerFont(TTFont(f"{FONT_NAME}-Bold", FONT_PATH_BOLD))
        logger.info("تم تسجيل الخط العريض بنجاح")
    else:
        logger.warning("ملف الخط العريض غير موجود، سيتم استخدام العادي للعناوين.")
except Exception as e:
    logger.error(f"خطأ في تحميل الخطوط: {e}")
    FONT_NAME = "Helvetica"

def clean_text_for_pdf(text):
    """إزالة أو استبدال الرموز غير المدعومة"""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "💰": "اقتصادي", "🪶": "خفيف", "🛡️": "آمن",
        "🔴": "عالية", "🟡": "متوسطة", "🟢": "منخفضة",
        "✅": "تم الحل", "⏳": "مفتوح", "📊": "نتائج", "⚠️": "تحذير",
    }
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
    return text

def reshape_arabic(text):
    """تشكيل النص العربي للعرض الصحيح مع تنظيف الرموز أولاً"""
    if not text:
        return ""
    try:
        cleaned = clean_text_for_pdf(text)
        reshaped = arabic_reshaper.reshape(cleaned)
        return get_display(reshaped)
    except Exception as e:
        logger.error(f"خطأ في تشكيل النص العربي: {e}")
        return text  # في حالة الفشل، نعيد النص الأصلي

def draw_header(c, project_name, width, height):
    """رسم ترويسة احترافية"""
    # شريط علوي
    c.setFillColor(colors.HexColor("#005f73"))  # أزرق هندسي
    c.rect(0, height - 40, width, 40, fill=1, stroke=0)

    # عنوان التقرير
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME, 16)
    title = reshape_arabic("تقرير مشروع هندسي")
    c.drawCentredString(width / 2, height - 28, title)

    # اسم المشروع
    c.setFillColor(colors.black)
    c.setFont(FONT_NAME, 12)
    p_name = reshape_arabic(f"المشروع: {project_name}")
    c.drawRightString(width - 50, height - 55, p_name)

    # التاريخ
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_txt = reshape_arabic(f"التاريخ: {date_str}")
    c.drawString(50, height - 55, date_txt)

    # خط فاصل
    c.setStrokeColor(colors.HexColor("#eeeeee"))
    c.setLineWidth(1)
    c.line(50, height - 65, width - 50, height - 65)

    return height - 80  # نقطة البداية للمحتوى

def draw_footer(c, width, height, page_num):
    """رسم التذييل"""
    c.setFont(FONT_NAME, 9)
    c.setFillColor(colors.gray)
    footer_text = reshape_arabic(f"صفحة {page_num} - تم التوليد بواسطة BluePrint")
    c.drawCentredString(width / 2, 20, footer_text)

def generate_project_report(project_id):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"لم يتم العثور على مشروع بالمعرف {project_id}")
            return None

        analyses = db.query(Analysis).filter(Analysis.project_id == project_id).order_by(Analysis.created_at.desc()).all()
        boqs = db.query(BOQItem).filter(BOQItem.project_id == project_id).all()
        defects = db.query(Defect).filter(Defect.project_id == project_id).all()
        site_visits = db.query(SiteVisit).filter(SiteVisit.project_id == project_id).order_by(SiteVisit.visit_date.desc()).limit(5).all()
        tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).all()  # NEW

        filename = f"report_{project_id}.pdf"
        c = canvas.Canvas(filename, pagesize=A4)
        w, h = A4

        # رسم الترويسة
        y = draw_header(c, project.name, w, h)

        # --- المهام (NEW) ---
        if tasks:
            y -= 20
            c.setFont(FONT_NAME, 14)
            c.setFillColor(colors.HexColor("#005f73"))
            c.drawRightString(w - 50, y, reshape_arabic("المهام المفتوحة"))
            y -= 20

            # نعرض أول 5 مهام فقط
            for task in tasks[:5]:
                if y < 100:
                    c.showPage()
                    y = draw_header(c, project.name, w, h) - 20

                # تنسيق لون حسب الأولوية
                priority_color = colors.black
                if task.priority == "عالية":
                    priority_color = colors.red
                elif task.priority == "متوسطة":
                    priority_color = colors.orange
                elif task.priority == "منخفضة":
                    priority_color = colors.green

                c.setFont(FONT_NAME, 10)
                c.setFillColor(priority_color)
                status_symbol = "●"
                if task.status == "منتهية":
                    status_symbol = "✅"
                elif task.status == "جاري":
                    status_symbol = "🔵"
                else:
                    status_symbol = "🟡"

                line = f"{status_symbol} {task.description} - {task.assignee} - أولوية: {task.priority} - تسليم: {task.due_date.strftime('%Y-%m-%d')}"
                draw_arabic_text(c, line, 70, y, 10)
                y -= 20
            y -= 10

        # --- العيوب ---
        y -= 20
        c.setFont(FONT_NAME, 14)
        c.setFillColor(colors.HexColor("#005f73"))
        c.drawRightString(w - 50, y, reshape_arabic("سجل العيوب والملاحظات"))
        y -= 10

        if defects:
            # إعداد بيانات الجدول
            table_data = [[
                reshape_arabic("الصورة"),
                reshape_arabic("الحالة"),
                reshape_arabic("الخطورة"),
                reshape_arabic("الوصف")
            ]]
            row_heights = [20]  # ارتفاع الصف الأول

            for d in defects[:10]:  # نعرض أول 10 عيوب
                status_text = reshape_arabic(d.status)
                severity_text = reshape_arabic(d.severity)
                desc_text = reshape_arabic(d.description[:30] + "..." if len(d.description) > 30 else d.description)

                # صورة العيب (إذا وجدت)
                img_text = reshape_arabic("لا توجد")
                if d.image_id:
                    img_file = db.query(UploadedFile).filter(UploadedFile.id == d.image_id).first()
                    if img_file and img_file.file_path and os.path.exists(img_file.file_path):
                        img_text = reshape_arabic("✅ موجودة")
                        # ملاحظة: يمكنك تطوير هذا لاحقاً لعرض الصورة الفعلية

                table_data.append([img_text, status_text, severity_text, desc_text])
                row_heights.append(25)

            # إنشاء الجدول: عرض الأعمدة [صورة(60), حالة(70), خطورة(70), وصف(300)]
            col_widths = [60, 70, 70, 300]
            t = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),  # خلفية الرأس
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # توسيط
                ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
            ]))

            # رسم الجدول
            t.wrapOn(c, w, h)
            t.drawOn(c, 50, y - t._height)
            y -= (t._height + 20)
        else:
            c.setFont(FONT_NAME, 10)
            c.drawRightString(w - 50, y, reshape_arabic("لا توجد عيوب مسجلة."))
            y -= 20

        # --- زيارات الموقع (تظل كما هي) ---
        if y < 150:
            c.showPage()
            y = draw_header(c, project.name, w, h) - 20

        y -= 20
        c.setFont(FONT_NAME, 14)
        c.setFillColor(colors.HexColor("#005f73"))
        c.drawRightString(w - 50, y, reshape_arabic("آخر زيارات الموقع"))
        y -= 10

        for visit in site_visits:
            if y < 100:
                c.showPage()
                y = draw_header(c, project.name, w, h) - 20
            line = f"- {visit.visit_date.strftime('%Y-%m-%d')}: {visit.location_name or 'بدون موقع'}"
            draw_arabic_text(c, line, 70, y, 10)
            y -= 20
            first_img = db.query(SiteVisitImage).filter(SiteVisitImage.site_visit_id == visit.id).first()
            if first_img and os.path.exists(first_img.image_path):
                try:
                    c.drawImage(first_img.image_path, 70, y-80, width=120, height=80, preserveAspectRatio=True)
                    y -= 100
                except:
                    pass
            y -= 10

        # --- جدول الكميات (BOQ) ---
        if y < 150:
            c.showPage()
            y = draw_header(c, project.name, w, h) - 20

        y -= 20
        c.setFont(FONT_NAME, 14)
        c.setFillColor(colors.HexColor("#005f73"))
        c.drawRightString(w - 50, y, reshape_arabic("جدول الكميات المالية"))
        y -= 10

        # تجميع بنود BOQ
        grouped_items = defaultdict(lambda: {"quantity": 0, "total_price": 0, "unit": ""})
        for item in boqs:
            key = item.description
            grouped_items[key]["quantity"] += item.quantity
            grouped_items[key]["total_price"] += item.total_price
            grouped_items[key]["unit"] = item.unit

        # إعداد بيانات الجدول
        boq_data = [[
            reshape_arabic("الإجمالي"),
            reshape_arabic("سعر الوحدة"),
            reshape_arabic("الكمية"),
            reshape_arabic("البند")
        ]]
        total_cost = 0

        for desc, values in grouped_items.items():
            total_cost += values["total_price"]
            unit_price = values["total_price"] / values["quantity"] if values["quantity"] > 0 else 0
            boq_data.append([
                reshape_arabic(f"{values['total_price']:,.0f}"),
                reshape_arabic(f"{unit_price:,.0f}"),
                reshape_arabic(f"{values['quantity']} {values['unit']}"),
                reshape_arabic(desc[:20] + "..." if len(desc) > 20 else desc)
            ])

        # جدول BOQ
        t_boq = Table(boq_data, colWidths=[80, 80, 100, 240])
        t_boq.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ]))

        t_boq.wrapOn(c, w, h)
        t_boq.drawOn(c, 50, y - t_boq._height)
        y -= (t_boq._height + 30)

        # إجمالي التكلفة
        c.setFont(FONT_NAME, 12)
        c.setFillColor(colors.black)
        c.drawRightString(w - 50, y, reshape_arabic(f"الإجمالي الكلي: {total_cost:,.0f} جنيه"))

        # التذييل
        draw_footer(c, w, h, 1)
        c.save()

        # قراءة الملف وإرجاع البايتات
        with open(filename, "rb") as f:
            pdf_bytes = f.read()
        os.remove(filename)
        return pdf_bytes

    except Exception as e:
        logger.error(f"خطأ في توليد تقرير المشروع: {e}", exc_info=True)
        return None
    finally:
        db.close()

def generate_daily_report(project_id, report_data):
    """تقرير يومي للموقع (نسخة محسنة)"""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"لم يتم العثور على مشروع بالمعرف {project_id}")
            return None

        filename = f"daily_report_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        c = canvas.Canvas(filename, pagesize=A4)
        w, h = A4

        # الترويسة
        y = draw_header(c, project.name, w, h)

        # بيانات أساسية في جدول بسيط
        y -= 20
        info_data = [
            [reshape_arabic("التاريخ:"), reshape_arabic(str(report_data.get('date', '')))],
            [reshape_arabic("الطقس:"), reshape_arabic(str(report_data.get('weather', '')))],
            [reshape_arabic("عدد العمال:"), reshape_arabic(str(report_data.get('workers_count', '')))],
            [reshape_arabic("المعدات:"), reshape_arabic(str(report_data.get('equipment', ''))[:30])],
        ]
        t_info = Table(info_data, colWidths=[100, 350])
        t_info.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        t_info.wrapOn(c, w, h)
        t_info.drawOn(c, 50, y - t_info._height)
        y -= (t_info._height + 30)

        # الملاحظات
        c.setFont(FONT_NAME, 12)
        c.setFillColor(colors.HexColor("#005f73"))
        c.drawRightString(w - 50, y, reshape_arabic("الملاحظات الفنية:"))
        y -= 20

        notes = report_data.get('notes', '').split('\n')
        for note in notes:
            if y < 100:
                c.showPage()
                y = draw_header(c, project.name, w, h) - 50

            # مربع خلفية خفيف للملاحظة
            c.setFillColor(colors.HexColor("#fafafa"))
            c.rect(50, y - 15, w - 100, 20, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawRightString(w - 60, y, reshape_arabic(note[:80]))
            y -= 25

        # صور الموقع (إذا وجدت)
        images = report_data.get('images', [])
        if images:
            y -= 20
            c.setFont(FONT_NAME, 12)
            c.setFillColor(colors.HexColor("#005f73"))
            c.drawRightString(w - 50, y, reshape_arabic("مرفقات صور:"))
            y -= 10

            # شبكة 2×2
            x_right = w - 180  # الصورة الأولى على اليمين
            x_left = 50        # الصورة الثانية على اليسار
            start_y = y

            for i, img_path in enumerate(images[:4]):  # نعرض أول 4 صور فقط
                try:
                    if os.path.exists(img_path):
                        current_x = x_right if i % 2 == 0 else x_left
                        current_y = start_y if i < 2 else start_y - 160
                        c.drawImage(img_path, current_x, current_y - 140, width=130, height=120,
                                    preserveAspectRatio=True, mask='auto')
                except Exception as img_e:
                    logger.error(f"خطأ في رسم الصورة {img_path}: {img_e}")

        # التذييل
        draw_footer(c, w, h, 1)
        c.save()

        with open(filename, "rb") as f:
            pdf_bytes = f.read()
        os.remove(filename)
        return pdf_bytes

    except Exception as e:
        logger.error(f"خطأ في توليد التقرير اليومي: {e}", exc_info=True)
        return None
    finally:
        db.close()
