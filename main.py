import sys
import os
import base64
import io
import logging
import json
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import func
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
import pandas as pd
import tempfile
import exifread
from geopy.geocoders import Nominatim
import redis
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

sys.stdout.reconfigure(encoding='utf-8')

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from database import (
    init_db, SessionLocal, 
    Project, Analysis, SiteReport, BOQItem, 
    UploadedFile, Defect, ProjectSettings,
    User, ProjectUser, SiteVisit, SiteVisitImage,
    MemoryEntry, Workflow, WorkflowLog,
    get_password_hash, verify_password
)

from orchestrator import route_request
from pdf_generator import generate_project_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

def get_secret_from_vault(secret_name):
    vault_url = os.getenv("AZURE_VAULT_URL")
    if vault_url and AZURE_AVAILABLE:
        try:
            credential = DefaultAzureCredential()
            secret_client = SecretClient(vault_url=vault_url, credential=credential)
            secret = secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.warning(f"فشل جلب {secret_name} من Vault: {e}")
    return None

SECRET_KEY = get_secret_from_vault("SECRET-KEY") or os.getenv("SECRET_KEY", "fallback-secret-key-change-in-production")
OPENAI_API_KEY = get_secret_from_vault("OPENAI-API-KEY") or os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = get_secret_from_vault("GEMINI-API-KEY") or os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = get_secret_from_vault("DEEPSEEK-API-KEY") or os.getenv("DEEPSEEK_API_KEY")
GROK_API_KEY = get_secret_from_vault("GROK-API-KEY") or os.getenv("GROK_API_KEY")
OPENROUTER_API_KEY = get_secret_from_vault("OPENROUTER-API-KEY") or os.getenv("OPENROUTER_API_KEY")
MISTRAL_API_KEY = get_secret_from_vault("MISTRAL-API-KEY") or os.getenv("MISTRAL_API_KEY")

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
if DEEPSEEK_API_KEY:
    os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY
if GROK_API_KEY:
    os.environ["GROK_API_KEY"] = GROK_API_KEY
if OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
if MISTRAL_API_KEY:
    os.environ["MISTRAL_API_KEY"] = MISTRAL_API_KEY

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("✅ Redis متصل")
except Exception as e:
    redis_client = None
    logger.warning(f"⚠️ Redis غير متاح: {e}")

scheduler = BackgroundScheduler()

def generate_daily_report_for_all_projects():
    db = SessionLocal()
    try:
        projects = db.query(Project).all()
        for project in projects:
            defects = db.query(Defect).filter(Defect.project_id == project.id).all()
            open_defects = [d for d in defects if d.status == "Open"]
            high_severity = [d for d in defects if d.severity == "High"]
            total_defects = len(defects)
            health_score = 100
            health_score -= len(open_defects) * 5
            health_score -= len(high_severity) * 10
            health_score = max(0, min(100, health_score))

            summary = f"مشروع {project.name}\n"
            summary += f"التاريخ: {datetime.now().strftime('%Y-%m-%d')}\n"
            summary += f"إجمالي العيوب: {total_defects}\n"
            summary += f"عيوب مفتوحة: {len(open_defects)}\n"
            summary += f"عيوب عالية الخطورة: {len(high_severity)}\n"
            summary += f"مؤشر الصحة: {health_score}%\n"

            logger.info(f"تقرير يومي لمشروع {project.id}:\n{summary}")
    finally:
        db.close()

scheduler.add_job(
    generate_daily_report_for_all_projects,
    trigger=CronTrigger(hour=18, minute=0),
    id="daily_report",
    replace_existing=True
)
scheduler.start()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

app = FastAPI(title="Engineering OS v9.0 - Enterprise Edition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database Initialized with Enterprise schema.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/health")
def health_check():
    return {"status": "ok", "redis": redis_client is not None, "scheduler": "running"}

# ---------- Endpoints المستخدمين والمشاريع ----------
@app.post("/register")
def register(username: str, email: str, password: str, full_name: str = "", role: str = "viewer"):
    if len(password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="كلمة المرور طويلة جداً. الحد الأقصى 72 حرفاً.")
    db = SessionLocal()
    try:
        if db.query(User).filter((User.username == username) | (User.email == email)).first():
            raise HTTPException(status_code=400, detail="Username or email already registered")
        hashed = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "username": user.username, "role": user.role}
    finally:
        db.close()

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if len(form_data.password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="كلمة المرور طويلة جداً. الحد الأقصى 72 حرفاً.")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name
    }

@app.post("/projects/{project_id}/add_user")
def add_user_to_project(
    project_id: int,
    user_id: int,
    permission: str = "read",
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        if not project or not user:
            raise HTTPException(status_code=404, detail="Project or User not found")
        existing = db.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user_id
        ).first()
        if existing:
            existing.permission = permission
        else:
            pu = ProjectUser(project_id=project_id, user_id=user_id, permission=permission)
            db.add(pu)
        db.commit()
        return {"success": True}
    finally:
        db.close()

@app.post("/create_project")
def create_project(
    name: str, 
    location: str = "Cairo",
    current_user: User = Depends(get_current_active_user)
):
    db = SessionLocal()
    try:
        proj = Project(name=name, location=location)
        db.add(proj)
        db.flush()
        pu = ProjectUser(project_id=proj.id, user_id=current_user.id, permission="admin")
        db.add(pu)
        db.commit()
        db.refresh(proj)
        logger.info(f"Created Project: {proj.name} by user {current_user.username}")
        return {"id": proj.id, "name": proj.name}
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/projects")
def get_projects(current_user: User = Depends(get_current_active_user)):
    db = SessionLocal()
    try:
        if current_user.role == "admin":
            projects = db.query(Project).all()
        else:
            projects = db.query(Project).join(ProjectUser).filter(ProjectUser.user_id == current_user.id).all()
        return [{"id": p.id, "name": p.name, "location": p.location} for p in projects]
    finally:
        db.close()

@app.delete("/project/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db = SessionLocal()
    try:
        project_user = db.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            db.delete(proj)
            db.commit()
            logger.info(f"Deleted Project ID: {project_id}")
        return {"success": True}
    finally:
        db.close()

# ---------- Endpoint جلب بيانات المشروع مع Health Score ----------
@app.get("/project_data/{project_id}")
def get_project_data(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    cache_key = f"project_data:{project_id}:user:{current_user.id}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"✅ استخدام cached data للمشروع {project_id}")
            return json.loads(cached)

    db = SessionLocal()
    try:
        project_user = db.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found"}

        analyses = db.query(Analysis).filter(Analysis.project_id == project_id).order_by(Analysis.created_at.desc()).all()
        boqs = db.query(BOQItem).filter(BOQItem.project_id == project_id).all()
        defects = db.query(Defect).filter(Defect.project_id == project_id).all()
        files = db.query(UploadedFile).filter(UploadedFile.project_id == project_id).all()

        total_cost = sum([b.total_price or 0 for b in boqs])

        open_defects = [d for d in defects if d.status == "Open"]
        high_severity = [d for d in defects if d.severity == "High"]
        health_score = 100
        health_score -= len(open_defects) * 5
        health_score -= len(high_severity) * 10
        health_score = max(0, min(100, health_score))

        result = {
            "project_info": {"name": project.name, "location": project.location},
            "timeline": [
                {
                    "type": "analysis", 
                    "date": a.created_at.strftime("%Y-%m-%d %H:%M"), 
                    "task": a.task_type,
                    "status": a.safety_status
                } for a in analyses
            ],
            "boq": {
                "items": [{"id": b.id, "desc": b.description, "unit": b.unit, "qty": b.quantity, "price": b.total_price} for b in boqs],
                "total_cost": total_cost
            },
            "defects": [
                {"id": d.id, "desc": d.description, "severity": d.severity, "status": d.status} for d in defects
            ],
            "files_count": len(files),
            "health_score": health_score,
        }

        if redis_client:
            redis_client.setex(cache_key, 300, json.dumps(result))

        return result
    finally:
        db.close()

# ---------- Endpoint المعالجة الرئيسي ----------
@app.post("/process")
async def process_request(
    message: str = Form(None),
    project_id: int = Form(...),
    file: UploadFile = File(None),
    history: str = Form("[]"),
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    file_bytes = await file.read() if file else None
    file_type = file.content_type if file else None

    db = SessionLocal()
    file_record = None

    try:
        if file_bytes and file:
            file_path = os.path.join(UPLOAD_DIR, f"{project_id}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            file_record = UploadedFile(
                project_id=project_id, 
                filename=file.filename, 
                file_type=file_type, 
                file_path=file_path,
                analyzed=True
            )
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            logger.info(f"File saved: {file.filename}")
    except Exception as e:
        logger.error(f"File saving error: {e}")
    finally:
        db.close()

    result = await route_request(message, file_bytes, file_type, project_id, json.loads(history))

    db = SessionLocal()
    try:
        domain = result.get("domain")
        results = result.get("results", {})
        
        if domain == "boq" and "boq_item" in results:
            item = results["boq_item"]
            new_item = BOQItem(
                project_id=project_id,
                description=item.get("description"),
                unit=item.get("unit"),
                quantity=item.get("quantity"),
                total_price=item.get("total_price", 0)
            )
            db.add(new_item)
        elif domain == "design":
            new_analysis = Analysis(
                project_id=project_id,
                task_type=result.get("task"),
                input_text=message,
                result_json=result,
                safety_status="Unsafe" if "⚠️ تحذير" in str(results) else "Safe"
            )
            db.add(new_analysis)
        elif domain == "site":
            if "checklist_data" in results:
                report = SiteReport(
                    project_id=project_id,
                    summary=message,
                    issues=json.dumps(results["checklist_data"])
                )
                db.add(report)
            if "⚠️ العيوب" in results:
                new_defect = Defect(
                    project_id=project_id,
                    description=results["⚠️ العيوب"],
                    severity="Medium",
                    status="Open",
                    image_id=file_record.id if file_record else None
                )
                db.add(new_defect)
        elif domain == "general" and message:
            new_analysis = Analysis(
                project_id=project_id,
                task_type="chat",
                input_text=message,
                result_json=result,
                safety_status="Safe"
            )
            db.add(new_analysis)

        db.commit()
        logger.info(f"Data saved for Project {project_id} - Domain: {domain}")
    except Exception as e:
        logger.error(f"Database Save Error: {e}")
        db.rollback()
    finally:
        db.close()

    return result

# ---------- Endpoint تصدير PDF ----------
@app.get("/export_pdf/{project_id}")
def export_pdf(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    try:
        pdf_bytes = generate_project_report(project_id)
        if pdf_bytes:
            return Response(
                content=pdf_bytes, 
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=report_{project_id}.pdf"}
            )
        return {"error": "Could not generate PDF"}
    except Exception as e:
        logger.error(f"PDF Export Error: {e}")
        return {"error": str(e)}

# ---------- Endpoint إضافة بند حصر ----------
@app.post("/add_boq/{project_id}")
def add_boq_item(
    project_id: int, 
    desc: str, 
    unit: str, 
    qty: float, 
    price: float,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        new_item = BOQItem(
            project_id=project_id,
            description=desc,
            unit=unit,
            quantity=qty,
            total_price=price
        )
        db.add(new_item)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Add BOQ error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# ---------- Endpoint حذف بند حصر ----------
@app.delete("/boq/{boq_id}")
def delete_boq_item(
    boq_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db = SessionLocal()
    try:
        item = db.query(BOQItem).filter(BOQItem.id == boq_id).first()
        if not item:
            return {"error": "BOQ item not found"}
        project_user = db.query(ProjectUser).filter(
            ProjectUser.project_id == item.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        db.delete(item)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Delete BOQ error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# ---------- Endpoint تعديل عيب ----------
@app.put("/defect/{defect_id}")
def update_defect(
    defect_id: int, 
    description: str = None, 
    severity: str = None, 
    status: str = None,
    current_user: User = Depends(get_current_active_user)
):
    db = SessionLocal()
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            return {"error": "Defect not found"}
        project_user = db.query(ProjectUser).filter(
            ProjectUser.project_id == defect.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        if description:
            defect.description = description
        if severity:
            defect.severity = severity
        if status:
            defect.status = status
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Update defect error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# ---------- Endpoint حذف عيب ----------
@app.delete("/defect/{defect_id}")
def delete_defect(
    defect_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db = SessionLocal()
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            return {"error": "Defect not found"}
        project_user = db.query(ProjectUser).filter(
            ProjectUser.project_id == defect.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        db.delete(defect)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Delete defect error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# ---------- Endpoint إعدادات المشروع ----------
@app.get("/project_settings/{project_id}")
def get_project_settings(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        settings = db.query(ProjectSettings).filter(ProjectSettings.project_id == project_id).first()
        if not settings:
            settings = ProjectSettings(project_id=project_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return {
            "concrete_price": settings.concrete_price,
            "steel_price": settings.steel_price,
            "preferred_ai_model": settings.preferred_ai_model
        }
    finally:
        db.close()

@app.post("/project_settings/{project_id}")
def save_project_settings(
    project_id: int, 
    concrete_price: float, 
    steel_price: float, 
    preferred_ai_model: str,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        settings = db.query(ProjectSettings).filter(ProjectSettings.project_id == project_id).first()
        if not settings:
            settings = ProjectSettings(project_id=project_id)
            db.add(settings)
        settings.concrete_price = concrete_price
        settings.steel_price = steel_price
        settings.preferred_ai_model = preferred_ai_model
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Save settings error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# ---------- Endpoint إحصائيات المشروع ----------
@app.get("/project_stats/{project_id}")
def project_stats(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        analyses_count = db.query(Analysis).filter(Analysis.project_id == project_id).count()
        files_count = db.query(UploadedFile).filter(UploadedFile.project_id == project_id).count()
        defects_count = db.query(Defect).filter(Defect.project_id == project_id).count()
        total_cost = db.query(func.sum(BOQItem.total_price)).filter(BOQItem.project_id == project_id).scalar() or 0
        return {
            "analyses_count": analyses_count,
            "files_count": files_count,
            "defects_count": defects_count,
            "total_cost": total_cost
        }
    finally:
        db.close()

# ---------- Endpoint تصدير BOQ إلى Excel ----------
@app.get("/export_boq/{project_id}")
def export_boq_excel(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        boqs = db.query(BOQItem).filter(BOQItem.project_id == project_id).all()
        if not boqs:
            return {"error": "No BOQ items"}
        data = []
        for b in boqs:
            data.append({
                "الوصف": b.description,
                "الوحدة": b.unit,
                "الكمية": b.quantity,
                "السعر الإجمالي": b.total_price
            })
        df = pd.DataFrame(data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            df.to_excel(tmp.name, index=False)
            return FileResponse(tmp.name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"boq_project_{project_id}.xlsx")
    except Exception as e:
        logger.error(f"Export BOQ error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# ---------- Endpoints تقارير الموقع ----------
@app.post("/upload_site_visit/{project_id}")
async def upload_site_visit(
    project_id: int,
    location_name: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    notes: str = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        site_visit = SiteVisit(
            project_id=project_id,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            notes=notes,
            created_by=current_user.id
        )
        db.add(site_visit)
        db.flush()

        if files:
            for file in files:
                if file.content_type.startswith("image/"):
                    contents = await file.read()
                    tags = exifread.process_file(io.BytesIO(contents), details=False)
                    date_taken = None
                    if 'EXIF DateTimeOriginal' in tags:
                        date_str = str(tags['EXIF DateTimeOriginal'])
                        try:
                            date_taken = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        except:
                            pass
                    file_path = os.path.join(UPLOAD_DIR, f"site_{project_id}_{file.filename}")
                    with open(file_path, "wb") as f:
                        f.write(contents)
                    img_record = SiteVisitImage(
                        site_visit_id=site_visit.id,
                        image_path=file_path,
                        caption=file.filename,
                        timestamp=date_taken
                    )
                    db.add(img_record)
        db.commit()
        return {"success": True, "site_visit_id": site_visit.id}
    except Exception as e:
        logger.error(f"Upload site visit error: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/site_visits/{project_id}")
def get_site_visits(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        visits = db.query(SiteVisit).filter(SiteVisit.project_id == project_id).order_by(SiteVisit.visit_date.desc()).all()
        result = []
        for v in visits:
            images = db.query(SiteVisitImage).filter(SiteVisitImage.site_visit_id == v.id).all()
            result.append({
                "id": v.id,
                "visit_date": v.visit_date.isoformat(),
                "location_name": v.location_name,
                "latitude": v.latitude,
                "longitude": v.longitude,
                "notes": v.notes,
                "images": [{"path": img.image_path, "caption": img.caption} for img in images]
            })
        return result
    finally:
        db.close()

# ---------- Endpoints الذاكرة (Memory Bank) ----------
@app.post("/memory/{project_id}")
def add_memory_entry(
    project_id: int,
    entry_type: str,
    title: str,
    content: str,
    tags: str = "",
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        memory = MemoryEntry(
            project_id=project_id,
            entry_type=entry_type,
            title=title,
            content=content,
            tags=tags
        )
        db.add(memory)
        db.commit()
        return {"success": True, "id": memory.id}
    except Exception as e:
        logger.error(f"Add memory error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/memory/{project_id}")
def get_memory_entries(
    project_id: int,
    entry_type: str = None,
    tag: str = None,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        query = db.query(MemoryEntry).filter(MemoryEntry.project_id == project_id)
        if entry_type:
            query = query.filter(MemoryEntry.entry_type == entry_type)
        if tag:
            query = query.filter(MemoryEntry.tags.contains(tag))
        entries = query.order_by(MemoryEntry.created_at.desc()).all()
        return [
            {
                "id": e.id,
                "entry_type": e.entry_type,
                "title": e.title,
                "content": e.content,
                "tags": e.tags,
                "created_at": e.created_at.isoformat()
            }
            for e in entries
        ]
    finally:
        db.close()

# ---------- Endpoints سير العمل (Workflows) ----------
@app.post("/workflows/{project_id}")
def create_workflow(
    project_id: int,
    name: str,
    trigger_event: str,
    action_type: str,
    action_params: dict,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create workflows")
    db = SessionLocal()
    try:
        workflow = Workflow(
            project_id=project_id,
            name=name,
            trigger_event=trigger_event,
            action_type=action_type,
            action_params=action_params
        )
        db.add(workflow)
        db.commit()
        return {"success": True, "id": workflow.id}
    except Exception as e:
        logger.error(f"Create workflow error: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/workflows/{project_id}")
def get_workflows(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        workflows = db.query(Workflow).filter(Workflow.project_id == project_id).all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "trigger_event": w.trigger_event,
                "action_type": w.action_type,
                "action_params": w.action_params,
                "is_active": w.is_active
            }
            for w in workflows
        ]
    finally:
        db.close()

@app.put("/workflows/{workflow_id}/toggle")
def toggle_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can modify workflows")
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            return {"error": "Workflow not found"}
        workflow.is_active = not workflow.is_active
        db.commit()
        return {"success": True, "is_active": workflow.is_active}
    finally:
        db.close()
        # ---------- Endpoint إضافة عيب يدوي ----------
@app.post("/add_defect/{project_id}")
def add_defect(
    project_id: int,
    description: str,
    severity: str = "Medium",
    status: str = "Open",
    current_user: User = Depends(get_current_active_user)
):
    # التحقق من الصلاحية
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and (not project_user or project_user.permission not in ["write", "admin"]):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    db = SessionLocal()
    try:
        new_defect = Defect(
            project_id=project_id,
            description=description,
            severity=severity,
            status=status
        )
        db.add(new_defect)
        db.commit()
        return {"success": True, "id": new_defect.id}
    except Exception as e:
        logger.error(f"Add defect error: {e}")
        return {"error": str(e)}
    finally:
        db.close()
            # ---------- Endpoint تصدير Word ----------
@app.get("/export_word/{project_id}")
def export_word(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    # التحقق من الصلاحية
    db_check = SessionLocal()
    try:
        project_user = db_check.query(ProjectUser).filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        if current_user.role != "admin" and not project_user:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    finally:
        db_check.close()

    try:
        word_bytes = generate_project_word(project_id)
        if word_bytes:
            return Response(
                content=word_bytes, 
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename=report_{project_id}.docx"}
            )
        return {"error": "Could not generate Word document"}
    except Exception as e:
        logger.error(f"Word Export Error: {e}")
        return {"error": str(e)}