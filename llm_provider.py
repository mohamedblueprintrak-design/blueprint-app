import os
import base64
import logging
import json
import asyncio
import hashlib
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("llm_provider")

# إعداد Redis (اختياري)
try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("🟢 [llm] Redis connected")
except:
    redis_client = None
    print("🔴 [llm] Redis not available")

# إعداد OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_CLIENT = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
except:
    OPENAI_CLIENT = None

# إعداد Mistral
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except:
    MISTRAL_AVAILABLE = False

# إعداد Gemini (مؤقتاً مع التعامل مع التحذير)
try:
    import google.generativeai as genai
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
except:
    pass

class LLMProvider:
    def __init__(self):
        self.models = {
            # ---------- Gemini ----------
            "gemini": {"type": "gemini", "model": "gemini-2.0-flash"},
            "gemini-lite": {"type": "gemini", "model": "gemini-2.0-flash-lite"},
            "gemini-25": {"type": "gemini", "model": "gemini-2.5-flash"},
            
            # ---------- OpenAI ----------
            "gpt-4o": {"type": "openai", "model": "gpt-4o", "client": OPENAI_CLIENT},
            "gpt-3.5": {"type": "openai", "model": "gpt-3.5-turbo", "client": OPENAI_CLIENT},
            
            # ---------- DeepSeek ----------
            "deepseek": {"type": "openai_compat", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
            "deepseek-r1": {"type": "openai_compat", "base_url": "https://api.deepseek.com", "model": "deepseek-reasoner"},
            
            # ---------- Wisdom Gate ----------
            "deepseek-free": {
                "type": "openai_compat",
                "base_url": "https://wisdom-gate.juheapi.com/v1",
                "model": "deepseek/deepseek-r1"
            },
            
            # ---------- OpenRouter ----------
            "openrouter-llama32-3b": {
                "type": "openai_compat",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "api_key_name": "OPENROUTER_API_KEY"
            },
            "openrouter-gemma3-4b": {
                "type": "openai_compat",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "google/gemma-3-4b-it:free",
                "api_key_name": "OPENROUTER_API_KEY"
            },
            "openrouter-gemma3n-4b": {
                "type": "openai_compat",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "google/gemma-3n-4b-it:free",
                "api_key_name": "OPENROUTER_API_KEY"
            },
            "openrouter-gemma3-12b": {
                "type": "openai_compat",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "google/gemma-3-12b-it:free",
                "api_key_name": "OPENROUTER_API_KEY"
            },
            "openrouter-gemma3n-2b": {
                "type": "openai_compat",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "google/gemma-3n-e2b-it:free",
                "api_key_name": "OPENROUTER_API_KEY"
            },
            "openrouter-zai-glm": {
                "type": "openai_compat",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "z-ai/glm-4.5-air:free",
                "api_key_name": "OPENROUTER_API_KEY"
            },
            
            # ---------- Mistral ----------
            "mistral-small": {
                "type": "mistral",
                "model": "mistral-small-latest",
                "api_key_name": "MISTRAL_API_KEY"
            },
            "mistral-medium": {
                "type": "mistral",
                "model": "mistral-medium-latest",
                "api_key_name": "MISTRAL_API_KEY"
            },
            "mistral-large": {
                "type": "mistral",
                "model": "mistral-large-latest",
                "api_key_name": "MISTRAL_API_KEY"
            },
            
            # ---------- HuggingFace ----------
            "huggingface-llama-3.2-3b": {
                "type": "openai_compat",
                "base_url": "https://api-inference.huggingface.co/v1/",
                "model": "meta-llama/Llama-3.2-3B-Instruct",
                "api_key_name": "HUGGINGFACE_API_KEY"
            },
            "huggingface-llama-3.1-8b": {
                "type": "openai_compat",
                "base_url": "https://api-inference.huggingface.co/v1/",
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "api_key_name": "HUGGINGFACE_API_KEY"
            },
            "huggingface-mistral-7b": {
                "type": "openai_compat",
                "base_url": "https://api-inference.huggingface.co/v1/",
                "model": "mistralai/Mistral-7B-Instruct-v0.3",
                "api_key_name": "HUGGINGFACE_API_KEY"
            },
            "huggingface-gemma-2-2b": {
                "type": "openai_compat",
                "base_url": "https://api-inference.huggingface.co/v1/",
                "model": "google/gemma-2-2b-it",
                "api_key_name": "HUGGINGFACE_API_KEY"
            },
            "huggingface-qwen-2.5-7b": {
                "type": "openai_compat",
                "base_url": "https://api-inference.huggingface.co/v1/",
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "api_key_name": "HUGGINGFACE_API_KEY"
            },
            
            # ---------- Grok ----------
            "grok": {"type": "openai_compat", "base_url": "https://api.x.ai/v1", "model": "grok-1"},
        }
        print("🟢 [llm] LLMProvider initialized")

    async def _get_client(self, model_key):
        config = self.models.get(model_key)
        if not config:
            return None, None

        if config["type"] in ["openai", "openai_compat"]:
            if config.get("client"):
                return config["client"], config["model"]

            if "api_key_name" in config:
                key_name = config["api_key_name"]
            else:
                key_name = f"{model_key.upper()}_API_KEY"

            api_key = os.getenv(key_name)
            if api_key:
                try:
                    client = AsyncOpenAI(api_key=api_key, base_url=config.get("base_url"))
                    return client, config["model"]
                except Exception as e:
                    print(f"🔴 [llm] Failed to create client for {model_key}: {e}")
                    return None, None
        return None, None

    async def generate_text(self, prompt, model_preference=None):
        if model_preference is None:
            model_preference = [
                "gpt-4o-mini",      # تمت الإضافة
                "gemini-flash",      # تمت الإضافة
                "huggingface-llama-3.2-3b",
                "huggingface-llama-3.1-8b",
                "huggingface-mistral-7b",
                "huggingface-gemma-2-2b",
                "huggingface-qwen-2.5-7b",
                "mistral-small",
                "mistral-medium",
                "mistral-large",
                "openrouter-llama32-3b",
                "openrouter-gemma3-4b",
                "openrouter-zai-glm",
                "gemini",
                "deepseek-free",
                "gpt-4o"
            ]

        print(f"\n🟡 [llm] Trying models: {model_preference}")
        print(f"🟡 [llm] Prompt (first 100 chars): {prompt[:100]}...")

        for model_name in model_preference:
            print(f"🟡 [llm] Attempting model: {model_name}")
            try:
                if model_name.startswith("gemini"):
                    key = os.getenv("GEMINI_API_KEY")
                    if key:
                        import google.generativeai as genai
                        genai.configure(api_key=key)
                        model = genai.GenerativeModel(self.models[model_name]["model"])
                        res = await asyncio.to_thread(model.generate_content, prompt)
                        print(f"🟢 [llm] Gemini ({model_name}) succeeded")
                        return res.text
                    else:
                        print(f"🔴 [llm] Gemini key missing for {model_name}")
                        continue

                elif model_name.startswith("mistral"):
                    key = os.getenv("MISTRAL_API_KEY")
                    if key and MISTRAL_AVAILABLE:
                        from mistralai import Mistral
                        client = Mistral(api_key=key)
                        res = await client.chat.complete_async(
                            model=self.models[model_name]["model"],
                            messages=[{"role": "user", "content": prompt}]
                        )
                        print(f"🟢 [llm] Mistral ({model_name}) succeeded")
                        return res.choices[0].message.content
                    else:
                        print(f"🔴 [llm] Mistral key missing for {model_name}")
                        continue

                client, model_id = await self._get_client(model_name)
                if client:
                    res = await client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        timeout=15
                    )
                    print(f"🟢 [llm] {model_name} succeeded")
                    return res.choices[0].message.content
                else:
                    print(f"🔴 [llm] Client not available for {model_name}")
                    continue

            except Exception as e:
                print(f"🔴 [llm] Error with {model_name}: {e}")
                continue

        print("🔴 [llm] All models failed. Returning mock response for this request.")
        return self._mock_response(prompt)

    async def analyze_image(self, image_base64, prompt, model_preference=None):
        if model_preference is None:
            model_preference = ["gemini", "gpt-4o"]

        for model_name in model_preference:
            try:
                if model_name == "gemini":
                    key = os.getenv("GEMINI_API_KEY")
                    if key:
                        import google.generativeai as genai
                        genai.configure(api_key=key)
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        image_data = base64.b64decode(image_base64)
                        res = await asyncio.to_thread(
                            model.generate_content,
                            [prompt, {"mime_type": "image/jpeg", "data": image_data}]
                        )
                        return res.text
                    else:
                        continue
                elif model_name == "gpt-4o":
                    client, model_id = await self._get_client("gpt-4o")
                    if client:
                        res = await client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                                ]
                            }]
                        )
                        return res.choices[0].message.content
                    else:
                        continue
            except Exception as e:
                print(f"🔴 [llm] Vision model {model_name} failed: {e}")
                continue

        return "⚠️ لم أتمكن من تحليل الصورة."

    def _mock_response(self, prompt):
        prompt_lower = prompt.lower()
        import re
        if "كمرة" in prompt_lower or "beam" in prompt_lower:
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", prompt)
            length = 5.0
            load = 2.0
            if len(numbers) >= 2:
                length = float(numbers[0])
                load = float(numbers[1])
            elif len(numbers) == 1:
                length = float(numbers[0])
            return f"لتصميم كمرة ببساطة: إذا كان البحر {length} متر والحمل {load} طن/م، العمق التقريبي = {int(length*100)} سم، عرض 25 سم، حديد سفلي 4 قضبان 16 مم. التكلفة التقريبية {int(length*load*500)} جنيه."
        elif "طوب" in prompt_lower or "عدد الطوب" in prompt_lower:
            return "لحساب عدد الطوب: تحتاج إلى مساحة الحائط بالمتر المربع. عدد الطوب لكل متر مربع ≈ 60 طوبة (بمقاس 20×20×40). مثلاً لحائط 10 متر مربع، تحتاج 600 طوبة."
        elif "خرسانة" in prompt_lower or "concrete" in prompt_lower:
            return "نسب الخلط التقريبية: 1:2:4 (أسمنت:رمل:سن) للمتر المكعب. كمية الأسمنت ≈ 300-350 كجم."
        elif "سعر" in prompt_lower or "price" in prompt_lower:
            return "الأسعار التقريبية: حديد التسليح 35,000 جنيه/طن، الخرسانة 1,000 جنيه/م³ (قد تختلف حسب المنطقة والمورد)."
        elif "حديد" in prompt_lower or "steel" in prompt_lower:
            return "لحساب كمية الحديد: يمكن استخدام نسبة مئوية من حجم الخرسانة. في العناصر العادية، كمية الحديد ≈ 100-120 كجم/م³. لحساب دقيق، نحتاج إلى أبعاد العنصر وتفاصيل التسليح."
        else:
            return f"مرحباً! أنا Blue في وضع المحاكاة المؤقت. طلبك: '{prompt[:100]}...'. (للحصول على ردود حقيقية، يرجى تفعيل مفاتيح API المجانية)."

# هذا هو السطر الأهم – يجب أن يكون في نهاية الملف بدون أي مسافات بادئة
llm = LLMProvider()
print("🟢 [llm] LLM instance created")
