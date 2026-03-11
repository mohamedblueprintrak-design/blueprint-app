import re
import json
import logging
from llm_provider import llm

logger = logging.getLogger("classifier")

async def classify_with_llm(text):
    """استخدام LLM لتصنيف النص (دقة عالية)"""
    prompt = f"""
    أنت مساعد ذكي لتصنيف استفسارات المستخدم في نظام هندسي. قم بتحليل النص التالي وإرجاع JSON بالشكل التالي:
    {{
        "task": "beam_tool" أو "slab_tool" أو "column_tool" أو "foundation_tool" أو "retaining_wall_tool" أو "stair_tool" أو "checklist_tool" أو "site_report" أو "image_analysis" أو "pdf_analysis" أو "boq_tool" أو "ask_ai" أو "general_chat",
        "domain": "design" أو "site" أو "boq" أو "office" أو "ai" أو "general"
    }}
    
    النص: "{text}"
    
    المخرجات بصيغة JSON فقط.
    """
    try:
        # استخدام نموذج سريع ورخيص لهذه المهمة
        response = await llm.generate_text(prompt, model_preference=["gpt-4o-mini", "gemini-flash", "mistral-small"])
        # استخراج JSON من الرد
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            logger.warning("No JSON found in LLM response")
            return None
    except Exception as e:
        logger.error(f"Error in classify_with_llm: {e}")
        return None

def classify_request(text=None, file_bytes=None, file_type=None):
    # تصنيف الملفات أولاً
    if file_bytes and file_type:
        if "image" in file_type:
            return {"task": "image_analysis", "domain": "site"}
        if "pdf" in file_type:
            return {"task": "pdf_analysis", "domain": "office"}

    if not text:
        return {"task": "general_chat", "domain": "general"}

    # محاولة التصنيف باستخدام LLM (دقة عالية)
    try:
        import asyncio
        # نستخدم حلقة حدث جديدة أو الحالية
        loop = asyncio.get_event_loop()
        llm_result = loop.run_until_complete(classify_with_llm(text))
        if llm_result and "task" in llm_result and "domain" in llm_result:
            logger.info(f"LLM classification: {llm_result}")
            return llm_result
    except Exception as e:
        logger.warning(f"LLM classification failed, falling back to rules: {e}")

    # التصنيف بالقواعد (Fallback) - محسن ليشمل كلمات أكثر
    t = text.lower()

    # أدوات الموقع
    if any(word in t for word in ["تشك ليست", "checklist", "استلام", "مراجعة", "معاينة"]):
        return {"task": "checklist_tool", "domain": "site"}
    if any(word in t for word in ["تقرير موقع", "تقرير يومي", "تسجيل يومي", "حالة الطقس", "عدد العمال"]):
        return {"task": "site_report", "domain": "site"}

    # الحصر (BOQ) - نوسع الكلمات المفتاحية
    boq_keywords = ["حصر", "كمية", "كميات", "حديد", "خرسانة", "بلوك", "أسمنت", "رمل", "سن", "طوب", "نحسب", "حساب", "تكلفة", "سعر"]
    if any(word in t for word in boq_keywords):
        return {"task": "boq_tool", "domain": "boq"}

    # التصميم
    design_keywords = {
        "بلاطة": "slab_tool", "سقف": "slab_tool",
        "عمود": "column_tool",
        "كمرة": "beam_tool", "ميدة": "beam_tool",
        "أساس": "foundation_tool", "قاعدة": "foundation_tool",
        "جدار استنادي": "retaining_wall_tool",
        "سلم": "stair_tool"
    }
    for word, task in design_keywords.items():
        if word in t:
            return {"task": task, "domain": "design"}

    # استدعاء الذكاء الاصطناعي العام
    if any(word in t for word in ["اسأل الذكاء", "openai", "ai", "blue", "اسال", "سؤال"]):
        return {"task": "ask_ai", "domain": "ai"}

    return {"task": "general_chat", "domain": "general"}
