import os
import base64
import logging
from dotenv import load_dotenv
import cv2
import numpy as np

# OpenAI Setup
load_dotenv()
logger = logging.getLogger("ai_integration")

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_ENABLED = True
except:
    OPENAI_ENABLED = False
    logger.warning("OpenAI Key not found. AI features disabled.")

# YOLO Setup
YOLO_MODEL = None
try:
    from ultralytics import YOLO
    if os.path.exists("models/yolov8n.pt"):
        YOLO_MODEL = YOLO("models/yolov8n.pt")
except:
    pass

def analyze_image_openai(image_base64, prompt):
    """تحليل صورة باستخدام GPT-4o"""
    if not OPENAI_ENABLED: return "AI Service not configured."
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # النموذج اللي بيشوف صور
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ],
                }
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def detect_objects_yolo(image_bytes):
    """اكتشاف العناصر في الصورة باستخدام YOLO"""
    if not YOLO_MODEL: return []
    
    # تحويل الصورة لـ numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    results = YOLO_MODEL(img)
    detections = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = YOLO_MODEL.names[cls_id]
            conf = float(box.conf[0])
            detections.append({"label": label, "confidence": conf})
            
    return detections

def ask_openai(prompt, context=None):
    if not OPENAI_ENABLED: return "AI Service unavailable."
    try:
        msgs = [{"role": "system", "content": "You are Blue, an expert engineering assistant."}]
        if context: msgs.append({"role": "system", "content": f"Context: {context}"})
        msgs.append({"role": "user", "content": prompt})
        
        res = client.chat.completions.create(model="gpt-4o-mini", messages=msgs)
        return res.choices[0].message.content
    except Exception as e:
        return str(e)