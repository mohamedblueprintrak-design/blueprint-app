import re
import json
import logging
from llm_provider import llm

logger = logging.getLogger("classifier")

async def classify_with_llm(text):
    """استخدام LLM لتصنيف النص"""
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

    # محاولة التصنيف باستخدام LLM (إذا كان النص طويلاً أو غير واضح)
    if len(text) > 15:
        try:
            import asyncio
            llm_result = asyncio.run(classify_with_llm(text))
            if llm_result and "task" in llm_result and "domain" in llm_result:
                logger.info(f"LLM classification: {llm_result}")
                return llm_result
        except Exception as e:
            logger.warning(f"LLM classification failed, falling back to rules: {e}")

    # التصنيف بالقواعد (Fallback)
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
