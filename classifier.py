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

    # ========== 1. القواعد الهندسية الصارمة (Priority 1) ==========
    
    # أ- التصميم الإنشائي (أهم حاجة)
    # لو فيه أرقام (أبعاد) + كلمة إنشائية -> تصميم
    has_numbers = bool(re.search(r'\d', t))
    
    # قاموس شامل للعناصر الإنشائية
    structural_elements = {
        "كمرة": "beam_tool", "beam": "beam_tool", "ميدة": "beam_tool",
        "بلاطة": "slab_tool", "سقف": "slab_tool", "slab": "slab_tool",
        "عمود": "column_tool", "column": "column_tool",
        "قاعدة": "foundation_tool", "أساس": "foundation_tool", "foundation": "foundation_tool",
        "سلم": "stair_tool", "stair": "stair_tool",
        "جدار استنادي": "retaining_wall_tool", "retaining wall": "retaining_wall_tool"
    }

    for keyword, task in structural_elements.items():
        if keyword in t:
            # لو فيه أرقام، يبقى أكيد تصميم
            if has_numbers:
                return {"task": task, "domain": "design"}
            # لو مفيش أرقام، ممكن يكون سؤال عام "ايه هي الكمرة؟"، نوجهه للمحادثة العامة
            # إلا لو الكلمة صريحة زي "صمم" أو "حساب"
            if any(word in t for word in ["صمم", "حساب", "تصميم", "design", "calculate"]):
                return {"task": task, "domain": "design"}

    # ب- الحصر (BOQ)
    boq_keywords = ["حصر", "كمية", "كميات", "حديد", "خرسانة", "بلوك", "أسمنت", "رمل", "طوب", 
                    "نحسب", "حساب", "تكلفة", "سعر", "boq", "ton", "m3", "طن", "متر مكعب"]
    if any(word in t for word in boq_keywords):
        return {"task": "boq_tool", "domain": "boq"}

    # ج- الموقع والتقارير
    site_keywords = ["تشك ليست", "checklist", "استلام", "مراجعة", "معاينة", "موقع"]
    if any(word in t for word in site_keywords):
        return {"task": "checklist_tool", "domain": "site"}
    
    report_keywords = ["تقرير موقع", "تقرير يومي", "تسجيل يومي", "حالة الطقس", "عدد العمال"]
    if any(word in t for word in report_keywords):
        return {"task": "site_report", "domain": "site"}

    # ========== 2. قواعد السياق (Context Awareness) ==========
    
    # لو الجملة فيها أرقام كتير ومفيش كلمات مفتاحية -> ممكن يكون تصميم ضImplicit
    # مثال: "5 متر 2 طن" من غير كلمة كمرة -> نعتبره طلب تصميم عام
    if has_numbers and len(re.findall(r'\d+', t)) >= 2:
        # لو الجملة قصيرة وفيها أرقام -> تصميم
        if len(t.split()) < 10:
             return {"task": "beam_tool", "domain": "design"}

    # ========== 3. الذكاء الاصطناعي (LLM Fallback) ==========
    # لو مفيش أي قاعدة اشتغلت، نبعت للـ AI يحاول يفهم
    if len(t) > 10:
        try:
            import asyncio
            prompt = f"""
            Analyze this user request and determine the domain.
            Possible domains: 'design' (structural calculations), 'boq' (quantity takeoff), 'site' (site reports/checklists), 'general' (general engineering chat).
            Return JSON: {{"domain": "...", "task": "..."}}
            
            Text: "{text}"
            """
            # هنا بنستخدم الموديلز المجانية اللي اشتغلت في الاختبار
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(llm.generate_text(prompt, model_preference=["gemini-flash", "mistral-small", "gpt-4o-mini"]))
            loop.close()
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # لو الـ AI قال "design" أو "boq"، نصدقه
                if result.get("domain") in ["design", "boq", "site"]:
                    # نضبط الـ task name
                    task = result.get("task", "general_chat")
                    if result["domain"] == "design": task = "beam_tool"
                    if result["domain"] == "boq": task = "boq_tool"
                    return {"task": task, "domain": result["domain"]}
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")

    # ========== 4. الوضع الافتراضي (General Chat) ==========
    # لو كل المحاولات فشلت، نخليه يتكلم كـ "Blue" المهندس العام
    return {"task": "general_chat", "domain": "general"}
