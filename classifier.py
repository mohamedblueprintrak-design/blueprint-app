import re

def classify_request(text=None, file_bytes=None, file_type=None):
    if file_bytes and file_type:
        if "image" in file_type:
            return {"task": "image_analysis", "domain": "site"}
        if "pdf" in file_type:
            return {"task": "pdf_analysis", "domain": "office"}

    if not text:
        return {"task": "general_chat", "domain": "general"}

    t = text.lower()

    # أدوات الموقع
    if "تشك ليست" in t or "checklist" in t or "استلام" in t:
        return {"task": "checklist_tool", "domain": "site"}
    if "تقرير موقع" in t or "تقرير يومي" in t:
        return {"task": "site_report", "domain": "site"}

    # الحصر
    if "حصر" in t or "كمية" in t or "حديد" in t or "خرسانة" in t or "بلوك" in t or "أسمنت" in t or "رمل" in t or "سن" in t:
        return {"task": "boq_tool", "domain": "boq"}

    # التصميم
    if "بلاطة" in t or "سقف" in t:
        return {"task": "slab_tool", "domain": "design"}
    if "عمود" in t:
        return {"task": "column_tool", "domain": "design"}
    if "كمرة" in t or "تحليل كمرة" in t:
        return {"task": "beam_tool", "domain": "design"}
    if "أساس" in t or "قاعدة" in t:
        return {"task": "foundation_tool", "domain": "design"}
    if "جدار استنادي" in t:
        return {"task": "retaining_wall_tool", "domain": "design"}
    if "سلم" in t:
        return {"task": "stair_tool", "domain": "design"}

    # استدعاء الذكاء الاصطناعي العام
    if "اسأل الذكاء" in t or "openai" in t or "ai" in t:
        return {"task": "ask_ai", "domain": "ai"}

    return {"task": "general_chat", "domain": "general"}