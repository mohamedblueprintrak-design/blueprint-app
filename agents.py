import logging
import json
from llm_provider import llm
from tools import (
    structural_beam_analysis, slab_analysis, column_analysis, 
    foundation_analysis, draw_beam_section, generate_beam_dxf,
    retaining_wall_analysis, stair_analysis
)
from rules_engine import check_structural_safety
from database import SessionLocal, ProjectSettings, MemoryEntry

logger = logging.getLogger("agents")

# --- 1. وكيل التصميم ---
class StructuralAgent:
    def __init__(self):
        self.name = "Blue-Struct"
    
    def analyze(self, text, nums):
        results = {}
        if "كمرة" in text or "ميدة" in text:
            res = structural_beam_analysis(nums[0] if nums else 5.0, nums[1] if len(nums)>1 else 2.0)
            if res["success"]:
                best = res["scenarios"][0] 
                safety = check_structural_safety(best['raw_values'])
                results["📊 النتائج"] = f"Best: {best['label']} | Depth: {best['depth_mm']}mm | Cost: {best['cost_egp']} EGP"
                if not safety["is_safe"]: results["⚠️ تحذير"] = "\n".join(safety["warnings"])
                bars = int(best['steel_bars'].split()[0])
                results["image_data"] = draw_beam_section(best['width_mm'], best['depth_mm'], bars)
                results["dxf_data"] = generate_beam_dxf(best['width_mm'], best['depth_mm'], bars)
        if "جدار استنادي" in text or "retaining wall" in text:
            height = nums[0] if nums else 3.0
            soil_load = nums[1] if len(nums)>1 else 20.0
            res = retaining_wall_analysis(height, soil_load)
            if res["success"]:
                results["📐 نتائج الجدار"] = res["results"]["explanation"]
                results["raw_values"] = res["results"]["raw_values"]
        if "سلم" in text or "stair" in text:
            floor_height = nums[0] if nums else 3.0
            res = stair_analysis(floor_height)
            if res["success"]:
                results["📐 نتائج السلم"] = res["results"]["explanation"]
                results["raw_values"] = res["results"]["raw_values"]
        return results

# --- 2. وكيل الرؤية ---
class VisionAgent:
    def __init__(self):
        self.name = "Blue-Vision"
    async def analyze_image(self, image_base64, prompt):
        return await llm.analyze_image(image_base64, prompt)
    async def detect_defects(self, image_base64):
        prompt = """
        Analyze this construction site image as a QC Engineer.
        Identify any visible defects (Honeycombing, Cracks, Exposed Rebar).
        Return JSON: {"defects": [{"type":"...", "severity":"High/Med/Low"}]}
        """
        return await llm.analyze_image(image_base64, prompt)

# --- 3. وكيل التقارير والمنطق (مع تفعيل الذاكرة) ---
class ReasoningAgent:
    def __init__(self):
        self.name = "Blue-Logic"
    
    async def generate_summary(self, data):
        prompt = f"""
        You are an expert engineer. Summarize this data in Arabic.
        Focus on safety and cost. 
        Data: {json.dumps(data)}
        """
        return await llm.generate_text(prompt, model_preference=["deepseek", "gpt-4o", "gemini"])

    async def chat(self, text, history=None, project_id=None):
        # جلب الذاكرة الخاصة بالمشروع
        memory_context = ""
        if project_id:
            try:
                db = SessionLocal()
                memories = db.query(MemoryEntry).filter(
                    MemoryEntry.project_id == project_id,
                    MemoryEntry.entry_type == 'chat'
                ).order_by(MemoryEntry.created_at.desc()).limit(5).all()
                
                if memories:
                    memory_lines = []
                    for m in memories:
                        memory_lines.append(f"{m.created_at.strftime('%Y-%m-%d')}: {m.content[:100]}")
                    memory_context = "ذكريات سابقة من هذا المشروع:\n" + "\n".join(memory_lines) + "\n\n"
                db.close()
            except Exception as e:
                logger.warning(f"Could not fetch memory: {e}")

        full_prompt = memory_context + text
        if history:
            context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
            full_prompt = f"Context of conversation:\n{context}\n\n{memory_context}User: {text}\nAssistant:"

        preferred_model = "gemini"
        if project_id:
            try:
                db = SessionLocal()
                settings = db.query(ProjectSettings).filter(ProjectSettings.project_id == project_id).first()
                if settings and settings.preferred_ai_model:
                    preferred_model = settings.preferred_ai_model
                db.close()
            except Exception as e:
                logger.warning(f"Could not fetch project settings: {e}")

        model_preference = [
            preferred_model,
            "mistral-small",
            "mistral-medium",
            "mistral-large",
            "openrouter-llama32-3b",
            "openrouter-gemma3-4b",
            "openrouter-gemma3n-4b",
            "openrouter-gemma3-12b",
            "openrouter-gemma3n-2b",
            "openrouter-zai-glm",
            "gemini",
            "gpt-4o",
            "deepseek",
            "grok"
        ]
        seen = set()
        unique_models = [m for m in model_preference if not (m in seen or seen.add(m))]

        response = await llm.generate_text(full_prompt, model_preference=unique_models)
        
        # حفظ المحادثة في الذاكرة
        if project_id and len(text) > 5:
            try:
                db = SessionLocal()
                memory = MemoryEntry(
                    project_id=project_id,
                    entry_type="chat",
                    title=f"User query: {text[:50]}",
                    content=f"Q: {text}\nA: {response[:200]}",
                    tags="chat,auto"
                )
                db.add(memory)
                db.commit()
                db.close()
            except Exception as e:
                logger.warning(f"Could not save memory: {e}")
        
        return response

# تهيئة الوكلاء
struct_agent = StructuralAgent()
vision_agent = VisionAgent()
reasoning_agent = ReasoningAgent()
