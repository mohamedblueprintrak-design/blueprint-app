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
    
    ملاحظة مهمة: كلمة "كمرة" تعني Beam (عنصر إنشائي) ولا تعني غرفة أو حيز معماري.
    
    النص: "{text}"
    
    المخرجات بصيغة JSON فقط.
    """
    try:
        response = await llm.generate_text(prompt, model_preference=["gpt-4o-mini", "gemini-flash", "mistral-small"])
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

    t = text.lower().strip()

    # ========== التصنيف بالقواعد (مُحسّن) ==========
    
    # 1. أولوية قصوى: التصميم الإنشائي (لأنها الأكثر دقة)
    # نبحث عن العبارات الأطول أولاً ثم الكلمات المفردة
    design_patterns = [
        ("كمرة خرسانية", "beam_tool"),
        ("تحليل كمرة", "beam_tool"),
        ("تصميم كمرة", "beam_tool"),
        ("كمرة", "beam_tool"),
        ("بلاطة", "slab_tool"),
        ("سقف", "slab_tool"),
        ("عمود", "column_tool"),
        ("أساس", "foundation_tool"),
        ("قاعدة", "foundation_tool"),
        ("جدار استنادي", "retaining_wall_tool"),
        ("سلم", "stair_tool"),
    ]
    
    for pattern, task in design_patterns:
        if pattern in t:
            # تأكد من أن السياق ليس عن غرفة أو بحر (لكن نعطي الأولية للكلمة)
            if "كمرة" in pattern and not any(word in t for word in ["غرفة", "بحر", "محيط", "شاطئ"]):
                return {"task": task, "domain": "design"}
            elif pattern != "كمرة":  # للعناصر الأخرى
                return {"task": task, "domain": "design"}

    # 2. أدوات الموقع
    site_keywords = ["تشك ليست", "checklist", "استلام", "مراجعة", "معاينة"]
    if any(word in t for word in site_keywords):
        return {"task": "checklist_tool", "domain": "site"}
    
    report_keywords = ["تقرير موقع", "تقرير يومي", "تسجيل يومي", "حالة الطقس", "عدد العمال"]
    if any(word in t for word in report_keywords):
        return {"task": "site_report", "domain": "site"}

    # 3. الحصر (BOQ)
    boq_keywords = ["حصر", "كمية", "كميات", "حديد", "خرسانة", "بلوك", "أسمنت", "رمل", "سن", "طوب", "نحسب", "حساب", "تكلفة", "سعر"]
    if any(word in t for word in boq_keywords):
        return {"task": "boq_tool", "domain": "boq"}

    # 4. استدعاء الذكاء الاصطناعي العام
    ai_keywords = ["اسأل الذكاء", "openai", "ai", "blue", "اسال", "سؤال"]
    if any(word in t for word in ai_keywords):
        return {"task": "ask_ai", "domain": "ai"}

    # 5. محاولة التصنيف باستخدام LLM (إذا كان النص طويلاً)
    if len(t) > 20:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            llm_result = loop.run_until_complete(classify_with_llm(text))
            loop.close()
            if llm_result and "task" in llm_result and "domain" in llm_result:
                logger.info(f"LLM classification: {llm_result}")
                return llm_result
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

    # 6. افتراضي
    return {"task": "general_chat", "domain": "general"}
