import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from passlib.context import CryptContext

SQLALCHEMY_DATABASE_URL = "postgresql://blueprint:gUSE6ak6O9CTLP0T2mrfqw6aUSkZ6YCM@dpg-d6mgrkdm5p6s73fqfnjg-a/blueprint_db_2kv6"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# ---------- نماذج المستخدمين والصلاحيات ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="viewer")  # admin, engineer, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("ProjectUser", back_populates="user")

class ProjectUser(Base):
    __tablename__ = "project_users"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    permission = Column(String, default="read")  # read, write, admin
    
    user = relationship("User", back_populates="projects")
    project = relationship("Project", back_populates="users")

# ---------- المشاريع ----------
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    analyses = relationship("Analysis", back_populates="project", cascade="all, delete-orphan")
    site_reports = relationship("SiteReport", back_populates="project", cascade="all, delete-orphan")
    boq_items = relationship("BOQItem", back_populates="project", cascade="all, delete-orphan")
    files = relationship("UploadedFile", back_populates="project", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="project", cascade="all, delete-orphan")
    users = relationship("ProjectUser", back_populates="project", cascade="all, delete-orphan")
    site_visits = relationship("SiteVisit", back_populates="project", cascade="all, delete-orphan")
    memory_entries = relationship("MemoryEntry", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="project", cascade="all, delete-orphan")

# ---------- التحليلات ----------
class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    task_type = Column(String)
    input_text = Column(Text)
    result_json = Column(JSON)
    safety_status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    project = relationship("Project", back_populates="analyses")

class SiteReport(Base):
    __tablename__ = "site_reports"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    report_date = Column(DateTime, default=datetime.utcnow)
    weather = Column(String)
    workers_count = Column(Integer)
    summary = Column(Text)
    issues = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="site_reports")

# ---------- حصر الكميات ----------
class BOQItem(Base):
    __tablename__ = "boq_items"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    description = Column(String)
    unit = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    total_price = Column(Float)
    project = relationship("Project", back_populates="boq_items")

# ---------- الملفات المرفوعة ----------
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    filename = Column(String)
    file_type = Column(String)
    file_path = Column(String)
    analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="files")

# ---------- العيوب ----------
class Defect(Base):
    __tablename__ = "defects"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    description = Column(Text)
    severity = Column(String)  # High, Medium, Low
    status = Column(String, default="Open")  # Open, Resolved
    image_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="defects")
    assignee = relationship("User", foreign_keys=[assigned_to])

# ---------- إعدادات المشروع ----------
class ProjectSettings(Base):
    __tablename__ = "project_settings"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True, index=True)
    concrete_price = Column(Float, default=1000.0)
    steel_price = Column(Float, default=35000.0)
    preferred_ai_model = Column(String, default="gemini")
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", backref="settings", uselist=False)

# ---------- زيارات الموقع ----------
class SiteVisit(Base):
    __tablename__ = "site_visits"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    visit_date = Column(DateTime, default=datetime.utcnow)
    location_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="site_visits")
    creator = relationship("User", foreign_keys=[created_by])
    images = relationship("SiteVisitImage", back_populates="site_visit", cascade="all, delete-orphan")

class SiteVisitImage(Base):
    __tablename__ = "site_visit_images"
    id = Column(Integer, primary_key=True, index=True)
    site_visit_id = Column(Integer, ForeignKey("site_visits.id"), index=True)
    image_path = Column(String)
    caption = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    site_visit = relationship("SiteVisit", back_populates="images")

# ---------- الذاكرة طويلة المدى ----------
class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    entry_type = Column(String)  # decision, pattern, context, progress
    title = Column(String)
    content = Column(Text)
    tags = Column(String)  # مفصول بفواصل
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="memory_entries")

# ---------- سير العمل الآلي ----------
class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    name = Column(String)
    trigger_event = Column(String)  # image_upload, defect_created, design_completed
    action_type = Column(String)    # notify, create_defect, update_boq, send_message
    action_params = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="workflows")

class WorkflowLog(Base):
    __tablename__ = "workflow_logs"
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    triggered_by = Column(String)
    status = Column(String)        # success, failed
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workflow = relationship("Workflow")

# ---------- دالة تهيئة قاعدة البيانات ----------
def init_db():
    Base.metadata.create_all(bind=engine)

# ---------- دوال مساعدة للمستخدمين ----------
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
