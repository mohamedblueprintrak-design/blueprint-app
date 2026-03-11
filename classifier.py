import re
import json
import logging
from llm_provider import llm

logger = logging.getLogger("classifier")

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

    # ========== التصنيف بالقواعد (أولوية قصوى) ==========
    
    # 1. التصميم الإنشائي - نبحث عن الكلمات المفتاحية بوضوح
    if "كمرة" in t or "beam" in t:
        # تأكد من أنها ليست "غرفة" أو "بحر" في سياق مختلف
        if not any(word in t for word in ["غرفة", "بحر", "محيط", "شاطئ"]):
            return {"task": "beam_tool", "domain": "design"}
    
    if "بلاطة" in t or "سقف" in t or "slab" in t:
        return {"task": "slab_tool", "domain": "design"}
    
    if "عمود" in t or "column" in t:
        return {"task": "column_tool", "domain": "design"}
    
    if "أساس" in t or "قاعدة" in t or "foundation" in t:
        return {"task": "foundation_tool", "domain": "design"}
    
    if "جدار استنادي" in t or "retaining wall" in t:
        return {"task": "retaining_wall_tool", "domain": "design"}
    
    if "سلم" in t or "stair" in t:
        return {"task": "stair_tool", "domain": "design"}

    # 2. الحصر (BOQ)
    boq_keywords = ["حصر", "كمية", "كميات", "حديد", "خرسانة", "بلوك", "أسمنت", "رمل", "سن", "طوب", "نحسب", "حساب", "تكلفة", "سعر", "boq"]
    if any(word in t for word in boq_keywords):
        return {"task": "boq_tool", "domain": "boq"}

    # 3. أدوات الموقع
    site_keywords = ["تشك ليست", "checklist", "استلام", "مراجعة", "معاينة"]
    if any(word in t for word in site_keywords):
        return {"task": "checklist_tool", "domain": "site"}
    
    report_keywords = ["تقرير موقع", "تقرير يومي", "تسجيل يومي", "حالة الطقس", "عدد العمال"]
    if any(word in t for word in report_keywords):
        return {"task": "site_report", "domain": "site"}

    # 4. استدعاء الذكاء الاصطناعي العام
    ai_keywords = ["اسأل الذكاء", "openai", "ai", "blue", "اسال", "سؤال"]
    if any(word in t for word in ai_keywords):
        return {"task": "ask_ai", "domain": "ai"}

    # 5. محاولة التصنيف باستخدام LLM (فقط للجمل المعقدة)
    if len(t) > 20:
        try:
            import asyncio
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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(llm.generate_text(prompt, model_preference=["gpt-4o-mini", "gemini-flash"]))
            loop.close()
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                if result and "task" in result and "domain" in result:
                    logger.info(f"LLM classification: {result}")
                    return result
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

    # 6. افتراضي
    return {"task": "general_chat", "domain": "general"}

async def classify_with_llm(text):
    """دالة مساعدة لاستخدامها من أماكن أخرى"""
    return classify_request(text)
