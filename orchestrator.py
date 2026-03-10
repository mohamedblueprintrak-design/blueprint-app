import os
import base64
import logging
import json
import re
import pypdf
from io import BytesIO
from classifier import classify_request
from agents import struct_agent, vision_agent, reasoning_agent
from tools import get_site_checklist, boq_steel_calculator, boq_concrete_calculator, update_unit_prices_from_db

# استيراد دالة استرجاع المعرفة
from knowledge_retriever import get_retriever

logger = logging.getLogger("orchestrator")

async def extract_pdf_text(file_bytes):
    try:
        reader = pypdf.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except:
        return ""

async def route_request(text=None, file_bytes=None, file_type=None, project_id=None, history=None):
    results = {}
    
    if project_id:
        update_unit_prices_from_db(project_id)
    
    # التوجيه المباشر للكمرات
    if text and ("كمرة" in text or "beam" in text.lower()):
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        results = struct_agent.analyze(text, nums)
        return {"task": "beam_tool", "results": results, "domain": "design"}
    
    # تصنيف الطلب
    classification = classify_request(text, file_type)
    task = classification.get("task", "chat")
    domain = classification.get("domain", "general")
    
    image_base64 = base64.b64encode(file_bytes).decode("utf-8") if file_bytes else None
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", text or "")

    # استرجاع المعرفة من قاعدة المعرفة
    knowledge_context = ""
    if text and len(text) > 10 and project_id:
        try:
            retriever = get_retriever()
            if retriever:
                docs = retriever.retrieve(text, k=3)
                if docs:
                    knowledge_context = retriever.format_context(docs)
                    logger.info(f"Retrieved {len(docs)} knowledge chunks for query: {text[:50]}...")
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")

    if domain == "design":
        results = struct_agent.analyze(text, nums)
        if results:
            enhanced_summary_prompt = f"{knowledge_context}\n\nلخص النتائج الهندسية التالية:\n{json.dumps(results)}"
            summary = await reasoning_agent.generate_summary({"text": enhanced_summary_prompt})
            results["🤖 ملخص ذكي"] = summary
        return {"task": task, "results": results, "domain": domain}

    if domain == "site":
        if task == "image_analysis" and image_base64:
            analysis = await vision_agent.analyze_image(image_base64, "حلل الصورة هندسياً")
            results["📷 التحليل"] = analysis
            defects = await vision_agent.detect_defects(image_base64)
            results["⚠️ العيوب"] = defects
        elif task == "checklist_tool" and text:
            work_type = "عام"
            if "نجارة" in text:
                work_type = "نجارة"
            elif "حدادة" in text:
                work_type = "حدادة"
            elif "صب" in text:
                work_type = "صب"
            checklist = get_site_checklist(work_type)
            results["📋 قائمة المراجعة"] = checklist["text"]
            results["checklist_data"] = checklist["items"]
        return {"task": task, "results": results, "domain": domain}

    if domain == "boq" and text:
        if "حديد" in text or "steel" in text.lower():
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
            if len(nums) >= 3:
                d, l, c = map(float, nums[:3])
                boq = boq_steel_calculator(d, l, c)
                if boq["success"]:
                    results["boq_item"] = boq["item"]
                    results["📦 بند حديد"] = f"{boq['item']['description']} - كمية {boq['item']['quantity']} طن - سعر {boq['item']['total_price']} جنيه"
        elif "خرسانة" in text or "concrete" in text.lower():
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
            if nums:
                v = float(nums[0])
                boq = boq_concrete_calculator(v)
                if boq["success"]:
                    results["boq_item"] = boq["item"]
                    results["📦 بند خرسانة"] = f"{boq['item']['description']} - كمية {boq['item']['quantity']} م³ - سعر {boq['item']['total_price']} جنيه"
        return {"task": task, "results": results, "domain": domain}

    if domain == "office" and file_bytes:
        pdf_text = await extract_pdf_text(file_bytes)
        summary = await reasoning_agent.generate_summary({"text": pdf_text[:2000]})
        results["📄 تحليل الملف"] = summary
        return {"task": task, "results": results, "domain": domain}

    if text:
        enhanced_prompt = text
        if knowledge_context:
            enhanced_prompt = f"معلومات مرجعية:\n{knowledge_context}\n\nسؤال المستخدم:\n{text}"
        res = await reasoning_agent.chat(enhanced_prompt, history=history, project_id=project_id)
        results["💻 Blue"] = res

    return {"task": task, "results": results, "domain": domain}
