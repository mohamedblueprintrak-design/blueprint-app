"""
BluePrint Engineering Consultancy - AI-Powered Engineering OS
واجهة المستخدم الرئيسية (Streamlit) - الإصدار النهائي مع جميع التحسينات
(Health Score, PWA, واتساب, رفع الملفات, السياق الذكي, تحسينات الموبايل)
"""

import streamlit as st
import requests
import base64
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import os
import urllib.parse

# إعدادات الصفحة
st.set_page_config(
    page_title="BluePrint Engineering",
    page_icon="🪄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة دعم PWA عبر HTML (manifest والأيقونات)
pwa_html = """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="BluePrint">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
    <meta name="theme-color" content="#0b2b4f">
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# ثوابت
<<<<<<< HEAD
BACKEND = "https://blueprint-app-jrwp.onrender.com"
=======
BACKEND = "https://blueprint-app-jrwp.onrender.com"  # عدّل الرابط حسب خدمتك
>>>>>>> a59f9d4 (تحسينات واجهة PWA وإصلاحات الموبايل)

# تهيئة session state
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None
if "language" not in st.session_state:
    st.session_state.language = "ar"  # ar / en
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

# دوال مساعدة
def switch_lang():
    st.session_state.language = "en" if st.session_state.language == "ar" else "ar"
    st.rerun()

def _(text_ar, text_en):
    """ترجمة بسيطة"""
    return text_ar if st.session_state.language == "ar" else text_en

def get_headers():
    """إرجاع headers مع التوكن إذا كان موجوداً"""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

# دالة للحصول على لون Health Score
def get_health_color(score):
    if score >= 70:
        return "🟢"
    elif score >= 40:
        return "🟡"
    else:
        return "🔴"

# CSS محسّن (عصري، متجاوب مع الموبايل)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/lucide-static@0.400.0/font/lucide.css');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    /* ترويسة المشروع */
    .project-header {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 1.5rem 2rem;
        border-radius: 1rem;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    .project-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    /* بطاقات الإحصائيات */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
        border: 1px solid #f0f0f0;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    }
    
    .metric-card h3 {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    .metric-card .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        line-height: 1.2;
    }
    
    /* بطاقة Health Score */
    .health-card {
        background: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 1.5rem;
        border: 2px solid;
        transition: transform 0.2s;
    }
    
    .health-card:hover {
        transform: translateY(-2px);
    }
    
    .health-score {
        font-size: 3rem;
        font-weight: 700;
        line-height: 1.2;
    }
    
    .health-label {
        font-size: 1.2rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    /* فقاعات المحادثة */
    .chat-message {
        padding: 1rem 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        max-width: 80%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 5px;
    }
    
    .assistant-message {
        background: white;
        color: #1e293b;
        margin-right: auto;
        border-bottom-left-radius: 5px;
        border-left: 5px solid #667eea;
    }
    
    .assistant-message::before {
        content: "🪄 Blue";
        display: block;
        font-size: 0.8rem;
        font-weight: 600;
        color: #667eea;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* أزرار مخصصة */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    
    /* شريط جانبي */
    [data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #f0f0f0;
    }
    
    [data-testid="stSidebar"] .sidebar-content {
        color: #1e293b;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }
    
    /* حقول الإدخال */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        border-radius: 0.5rem !important;
        border: 1px solid #e2e8f0;
        padding: 0.75rem 1rem !important;
        font-family: 'Cairo', sans-serif;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    }
    
    /* تبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: white;
        padding: 0.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* مربعات التحميل */
    .upload-area {
        border: 2px dashed #667eea;
        border-radius: 0.5rem;
        padding: 2rem;
        text-align: center;
        background: rgba(255,255,255,0.8);
        transition: all 0.2s;
    }
    
    .upload-area:hover {
        background: white;
        border-color: #764ba2;
    }
    
    /* تحسينات الموبايل */
    @media (max-width: 768px) {
        .chat-message {
            max-width: 90%;
        }
        .project-header h1 {
            font-size: 1.8rem;
        }
        .metric-card {
            margin-bottom: 1rem;
        }
        .stButton button {
            width: 100%;
        }
        [data-testid="column"] {
            width: 100% !important;
            flex: unset !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# تطبيق الوضع الليلي
if st.session_state.dark_mode:
    st.markdown("""
    <style>
        .stApp {
            background: #1a1a1a;
        }
        .metric-card {
            background: #2d2d2d;
            color: #ffffff;
        }
        .metric-card h3 {
            color: #a0a0a0;
        }
        .metric-card .metric-value {
            color: #ffffff;
        }
        .health-card {
            background: #2d2d2d;
            color: #ffffff;
        }
        .assistant-message {
            background: #2d2d2d;
            color: #ffffff;
            border-left: 5px solid #667eea;
        }
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            background: #3d3d3d;
            color: #ffffff;
            border-color: #555;
        }
    </style>
    """, unsafe_allow_html=True)

# الشريط الجانبي
with st.sidebar:
    col1, col2 = st.columns([1, 3])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=60)
        else:
            st.markdown("🪄", unsafe_allow_html=True)
    with col2:
        st.markdown("## BluePrint")
        st.markdown("##### Engineering Consultancy")
    
    st.markdown("---")
    
    # زر تبديل اللغة
    st.button(
        "🇺🇸 English" if st.session_state.language == "ar" else "🇸🇦 العربية",
        on_click=switch_lang,
        key="lang_btn",
        use_container_width=True
    )
    
    # الوضع الليلي
    if st.button(_("🌙 الوضع الليلي", "🌙 Dark Mode") if not st.session_state.dark_mode else _("☀️ الوضع العادي", "☀️ Light Mode"), key="dark_btn"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    
    st.markdown("---")
    
    # ---------- قسم المصادقة ----------
    if not st.session_state.token:
        st.markdown(f"### {_('🔐 تسجيل الدخول', '🔐 Login')}")
        tab1, tab2 = st.tabs([_("تسجيل دخول", "Login"), _("مستخدم جديد", "Register")])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input(_("اسم المستخدم", "Username"))
                password = st.text_input(_("كلمة المرور", "Password"), type="password")
                if st.form_submit_button(_("دخول", "Login"), use_container_width=True):
                    try:
                        r = requests.post(
                            f"{BACKEND}/token",
                            data={"username": username, "password": password}
                        )
                        if r.ok:
                            token_data = r.json()
                            st.session_state.token = token_data["access_token"]
                            # جلب بيانات المستخدم
                            user_r = requests.get(
                                f"{BACKEND}/users/me",
                                headers={"Authorization": f"Bearer {st.session_state.token}"}
                            )
                            if user_r.ok:
                                st.session_state.user = user_r.json()
                                st.success(_("✅ تم تسجيل الدخول", "✅ Login successful"))
                                st.rerun()
                            else:
                                st.error(_("❌ فشل في جلب بيانات المستخدم", "❌ Failed to get user data"))
                        else:
                            try:
                                err_detail = r.json().get("detail", "خطأ غير معروف")
                            except:
                                err_detail = f"خطأ {r.status_code}"
                            st.error(f"❌ {err_detail}")
                    except Exception as e:
                        st.error(f"❌ {str(e)}")
        
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input(_("اسم المستخدم", "Username"))
                new_email = st.text_input(_("البريد الإلكتروني", "Email"))
                new_password = st.text_input(
                    _("كلمة المرور", "Password"), 
                    type="password",
                    help=_("الحد الأقصى 72 حرفاً", "Maximum 72 characters")
                )
                new_fullname = st.text_input(_("الاسم الكامل", "Full Name"))
                if st.form_submit_button(_("تسجيل", "Register"), use_container_width=True):
                    if len(new_password) > 72:
                        st.error(_("❌ كلمة المرور طويلة جداً (الحد الأقصى 72 حرفاً)", "❌ Password too long (max 72 characters)"))
                    else:
                        try:
                            r = requests.post(
                                f"{BACKEND}/register",
                                params={
                                    "username": new_username,
                                    "email": new_email,
                                    "password": new_password,
                                    "full_name": new_fullname
                                }
                            )
                            if r.ok:
                                st.success(_("✅ تم التسجيل، يمكنك تسجيل الدخول الآن", "✅ Registered, you can login now"))
                            else:
                                try:
                                    err_detail = r.json().get("detail", "❌ فشل التسجيل")
                                except:
                                    err_detail = f"❌ خطأ {r.status_code}"
                                st.error(err_detail)
                        except Exception as e:
                            st.error(f"❌ {str(e)}")
    else:
        # عرض معلومات المستخدم
        st.markdown(f"### 👤 {st.session_state.user.get('full_name', st.session_state.user.get('username'))}")
        st.markdown(f"**{_('الدور', 'Role')}:** {st.session_state.user.get('role')}")
        if st.button(_("🚪 تسجيل خروج", "🚪 Logout"), key="logout_btn"):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.selected_project = None
            st.rerun()
    
    st.markdown("---")
    
    # باقي محتوى الشريط الجانبي (يظهر فقط إذا كان المستخدم مسجلاً)
    if st.session_state.token:
        # إنشاء مشروع جديد
        st.markdown(f"### {_('📁 مشروع جديد', '📁 New Project')}")
        with st.form("new_project", clear_on_submit=True):
            name = st.text_input(_("اسم المشروع", "Project Name"), placeholder=_("مثال: برج الأندلس", "Example: Andalusia Tower"))
            location = st.text_input(_("الموقع", "Location"), value="Cairo")
            if st.form_submit_button(_("🚀 إنشاء", "🚀 Create"), use_container_width=True):
                if name:
                    r = requests.post(
                        f"{BACKEND}/create_project",
                        params={"name": name, "location": location},
                        headers=get_headers()
                    )
                    if r.ok:
                        st.success(_("✅ تم إنشاء المشروع!", "✅ Project created!"))
                        time.sleep(1)
                        st.rerun()
        
        st.markdown("---")
        
        # اختيار مشروع موجود
        st.markdown(f"### {_('📂 المشاريع', '📂 Projects')}")
        try:
            projs = requests.get(f"{BACKEND}/projects", headers=get_headers()).json()
            if projs and isinstance(projs, list):
                proj_options = {f"{p['id']} - {p['name']} ({p['location']})": p['id'] for p in projs}
                selected_label = st.selectbox(
                    _("اختر مشروع", "Select Project"),
                    options=list(proj_options.keys())
                )
                if selected_label:
                    st.session_state.selected_project = proj_options[selected_label]
            else:
                st.info(_("✨ لا توجد مشاريع بعد، أنشئ أول مشروع", "✨ No projects yet, create your first project"))
        except Exception as e:
            st.error(_("🔌 لا يمكن الاتصال بالخادم", "🔌 Cannot connect to server"))
            st.stop()
        
        if st.session_state.selected_project:
            st.markdown("---")
            st.markdown(f"### {_('⚙️ الإجراءات', '⚙️ Actions')}")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(_("📄 PDF", "📄 PDF"), key="btn_pdf", use_container_width=True):
                    try:
                        pdf_url = f"{BACKEND}/export_pdf/{st.session_state.selected_project}"
                        with st.spinner(_("جاري تحضير التقرير...", "Preparing PDF...")):
                            response = requests.get(pdf_url, headers=get_headers())
                            if response.status_code == 200:
                                st.download_button(
                                    label=_("⬇️ تحميل PDF", "⬇️ Download PDF"),
                                    data=response.content,
                                    file_name=f"report_{st.session_state.selected_project}.pdf",
                                    mime="application/pdf"
                                )
                            else:
                                st.error(f"❌ فشل التحميل: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")
            with col2:
                if st.button(_("📝 Word", "📝 Word"), key="btn_word", use_container_width=True):
                    try:
                        word_url = f"{BACKEND}/export_word/{st.session_state.selected_project}"
                        with st.spinner(_("جاري تحضير ملف Word...", "Preparing Word...")):
                            response = requests.get(word_url, headers=get_headers())
                            if response.status_code == 200:
                                st.download_button(
                                    label=_("⬇️ تحميل Word", "⬇️ Download Word"),
                                    data=response.content,
                                    file_name=f"report_{st.session_state.selected_project}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                            else:
                                st.error(f"❌ فشل التحميل: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")
            with col3:
                if st.button(_("🗑️ حذف", "🗑️ Delete"), key="btn_delete", use_container_width=True):
                    if st.session_state.selected_project:
                        r = requests.delete(
                            f"{BACKEND}/project/{st.session_state.selected_project}",
                            headers=get_headers()
                        )
                        if r.ok:
                            st.success(_("✅ تم الحذف", "✅ Deleted"))
                            st.session_state.selected_project = None
                            st.rerun()
            
            # إعدادات المشروع
            with st.expander(_("⚙️ إعدادات المشروع", "⚙️ Project Settings")):
                try:
                    settings_resp = requests.get(
                        f"{BACKEND}/project_settings/{st.session_state.selected_project}",
                        headers=get_headers()
                    )
                    if settings_resp.ok:
                        settings = settings_resp.json()
                        conc_price = settings.get("concrete_price", 1000.0)
                        steel_price = settings.get("steel_price", 35000.0)
                        pref_model = settings.get("preferred_ai_model", "gemini")
                    else:
                        conc_price, steel_price, pref_model = 1000.0, 35000.0, "gemini"
                except:
                    conc_price, steel_price, pref_model = 1000.0, 35000.0, "gemini"

                with st.form("project_settings_form"):
                    new_conc = st.number_input(_("سعر الخرسانة (جنيه/م³)", "Concrete price (EGP/m³)"), value=conc_price, step=50.0)
                    new_steel = st.number_input(_("سعر الحديد (جنيه/طن)", "Steel price (EGP/ton)"), value=steel_price, step=500.0)
                    model_options = ["gemini", "gpt-4o", "deepseek", "grok", "mistral-small", "openrouter-llama32-3b", "openrouter-gemma3-4b", "openrouter-zai-glm", "huggingface-llama-3.2-3b"]
                    new_model = st.selectbox(_("النموذج المفضل", "Preferred AI model"), model_options, index=model_options.index(pref_model) if pref_model in model_options else 0)
                    if st.form_submit_button(_("💾 حفظ الإعدادات", "💾 Save Settings")):
                        try:
                            r = requests.post(
                                f"{BACKEND}/project_settings/{st.session_state.selected_project}",
                                params={"concrete_price": new_conc, "steel_price": new_steel, "preferred_ai_model": new_model},
                                headers=get_headers()
                            )
                            if r.ok:
                                st.success(_("✅ تم الحفظ", "✅ Saved"))
                        except:
                            st.error(_("❌ فشل الاتصال", "❌ Connection failed"))
            
            # قسم إدارة قاعدة المعرفة (للمشرفين فقط)
            if st.session_state.user.get('role') == 'admin':
                with st.expander(_("📚 إدارة قاعدة المعرفة", "📚 Knowledge Base Management")):
                    st.markdown(_("هنا يمكنك رفع ملفات PDF جديدة للكودات الهندسية.", "Here you can upload new PDF files for engineering codes."))
                    uploaded_files = st.file_uploader(
                        _("اختر ملفات PDF", "Choose PDF files"),
                        type=["pdf"],
                        accept_multiple_files=True,
                        key="kb_uploader"
                    )
                    if uploaded_files and st.button(_("💾 رفع وفهرسة الملفات", "💾 Upload and Index")):
                        # حفظ الملفات في مجلد knowledge_base
                        import os
                        os.makedirs("knowledge_base", exist_ok=True)
                        for uploaded_file in uploaded_files:
                            file_path = os.path.join("knowledge_base", uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getvalue())
                        st.success(_("✅ تم رفع الملفات. جاري إعادة الفهرسة...", "✅ Files uploaded. Re-indexing..."))
                        
                        # استدعاء إعادة الفهرسة
                        from knowledge_retriever import retriever
                        retriever.index_pdfs()
                        st.success(_("✅ تمت إعادة الفهرسة بنجاح", "✅ Re-indexing completed successfully"))
    else:
        st.info(_("🔐 الرجاء تسجيل الدخول أولاً", "🔐 Please login first"))

# المحتوى الرئيسي
if not st.session_state.token:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <h1 style="font-size: 4rem; color: #667eea;">🪄 BluePrint</h1>
        <h2 style="color: #4a5568; font-weight: 400;">Engineering Consultancy</h2>
        <p style="font-size: 1.2rem; color: #718096; margin-top: 2rem;">نظام تشغيل هندسي ذكي يعمل بالذكاء الاصطناعي</p>
        <div style="margin-top: 3rem;">
            <p style="color: #a0aec0;">الرجاء تسجيل الدخول من القائمة الجانبية</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not st.session_state.selected_project:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <h1 style="font-size: 3rem; color: #667eea;">👋 مرحباً بك</h1>
        <p style="font-size: 1.2rem; color: #4a5568;">اختر مشروعاً من القائمة الجانبية أو أنشئ مشروعاً جديداً</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# جلب بيانات المشروع
project_id = st.session_state.selected_project
try:
    response = requests.get(
        f"{BACKEND}/project_data/{project_id}",
        headers=get_headers()
    )
    if response.status_code != 200:
        st.error(f"❌ خطأ من الخادم: {response.status_code} - {response.text}")
        st.stop()
    data = response.json()
    if "error" in data:
        st.error(data["error"])
        st.stop()
except Exception as e:
    st.error(f"❌ فشل في تحميل بيانات المشروع: {str(e)}")
    st.stop()

# استخراج Health Score
health_score = data.get('health_score', 50)  # افتراضي 50 إذا لم يوجد
health_color = get_health_color(health_score)
health_status = _("ممتاز", "Excellent") if health_score >= 70 else (_("متوسط", "Average") if health_score >= 40 else _("خطر", "Critical"))

# عنوان المشروع مع Health Score
st.markdown(f"""
<div class="project-header">
    <h1>🏗️ {data['project_info']['name']}</h1>
    <p style="font-size: 1.2rem; opacity: 0.9;">
        📍 {data['project_info']['location']} | 
        🕒 {_('آخر تحديث', 'Last updated')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </p>
</div>
""", unsafe_allow_html=True)

# عرض Health Score في بطاقة منفصلة
st.markdown(f"""
<div class="health-card" style="border-color: {health_color};">
    <div style="display: flex; align-items: center; justify-content: center; gap: 20px;">
        <div>
            <span style="font-size: 4rem;">{health_color}</span>
        </div>
        <div>
            <div class="health-score">{health_score}%</div>
            <div class="health-label">{health_status}</div>
        </div>
    </div>
    <p style="margin-top: 10px; color: #718096;">{_('مؤشر صحة المشروع', 'Project Health Score')}</p>
</div>
""", unsafe_allow_html=True)

# تبويبات الواجهة
tab_names = [_("📊 لوحة المعلومات", "📊 Dashboard"),
             _("💬 المحادثة مع Blue", "💬 Chat with Blue"),
             _("📦 الحصر (BOQ)", "📦 BOQ"),
             _("🔍 العيوب", "🔍 Defects"),
             _("📋 الأرشيف", "📋 Archive"),
             _("📍 تقارير الموقع", "📍 Site Reports"),
             _("📚 قاعدة معرفية", "📚 Knowledge Base")]
tabs = st.tabs(tab_names)

# ========== لوحة المعلومات ==========
with tabs[0]:
    st.markdown(f"## {_('📈 نظرة عامة على المشروع', '📈 Project Overview')}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{_('📊 تحليلات', '📊 Analyses')}</h3>
            <div class="metric-value">{len(data.get('timeline', []))}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{_('📎 ملفات', '📎 Files')}</h3>
            <div class="metric-value">{data.get('files_count', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        total_cost = data.get('boq', {}).get('total_cost', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{_('💰 التكلفة', '💰 Cost')}</h3>
            <div class="metric-value">{total_cost:,.0f} {_('جنيه', 'EGP')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        defects_count = len(data.get('defects', []))
        st.markdown(f"""
        <div class="metric-card">
            <h3>{_('⚠️ عيوب', '⚠️ Defects')}</h3>
            <div class="metric-value">{defects_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if data.get('boq', {}).get('items'):
        df = pd.DataFrame(data['boq']['items'])
        fig = px.bar(df, x='desc', y='price', 
                     title=_('تكلفة بنود الحصر', 'BOQ Items Cost'),
                     labels={'desc': _('البند', 'Item'), 'price': _('السعر (جنيه)', 'Price (EGP)')},
                     color_discrete_sequence=['#667eea'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_family='Cairo',
            title_font_size=20,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(_("📉 لا توجد بيانات حصر كافية لإنشاء رسم بياني", "📉 No BOQ data to display chart"))

# ========== المحادثة مع Blue (مع رفع الملفات) ==========
with tabs[1]:
    st.markdown(f"## {_('💬 التحدث مع Blue', '💬 Chat with Blue')}")
    
    # عرض سجل المحادثة
    for msg in st.session_state.msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # منطقة رفع الملفات
    with st.expander(_("📎 رفع ملفات للتحليل", "📎 Upload files for analysis")):
        uploaded_files = st.file_uploader(
            _("اختر صور أو ملفات PDF", "Choose images or PDF files"),
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="chat_uploader"
        )
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} {_('ملف', 'file(s)')}")
    
    # منطقة الإدخال
    prompt = st.chat_input(_("اكتب طلبك هنا...", "Type your message..."), key="chat_main")
    
    if prompt or uploaded_files:
        # إضافة رسالة المستخدم إذا كان هناك نص
        if prompt:
            st.session_state.msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # إرسال الطلب إلى الخادم (مرة واحدة، مع أو بدون ملفات)
        with st.chat_message("assistant"):
            with st.spinner(_("Blue يفكر...", "Blue is thinking...")):
                try:
                    # تجهيز الملفات (إذا وجدت)
                    files = []
                    if uploaded_files:
                        for f in uploaded_files:
                            files.append(("files", (f.name, f.getvalue(), f.type)))
                    else:
                        files = None
                    
                    # بيانات الطلب
                    data_payload = {
                        "message": prompt or "",
                        "project_id": project_id,
                        "history": json.dumps(st.session_state.msgs[:-1] if prompt else st.session_state.msgs)
                    }
                    
                    response = requests.post(
                        f"{BACKEND}/process",
                        data=data_payload,
                        files=files,
                        headers=get_headers(),
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        results_dict = result.get("results", {})
                        if results_dict:
                            first_key = list(results_dict.keys())[0]
                            first_value = results_dict[first_key]
                            reply = first_value if isinstance(first_value, str) else str(first_value)
                        else:
                            reply = "لم أفهم، حاول مرة أخرى."
                        st.markdown(reply)
                        st.session_state.msgs.append({"role": "assistant", "content": reply})
                    else:
                        error_msg = f"❌ خطأ من الخادم: {response.status_code}"
                        st.error(error_msg)
                        st.session_state.msgs.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    st.error(f"❌ فشل الاتصال: {str(e)}")
                    st.session_state.msgs.append({"role": "assistant", "content": f"⚠️ خطأ: {str(e)}"})

# ========== الحصر (BOQ) ==========
with tabs[2]:
    st.subheader(_("📋 جدول الكميات والتكاليف", "📋 Bill of Quantities"))
    
    boq_items = data.get('boq', {}).get('items', [])
    if boq_items:
        df_boq = pd.DataFrame(boq_items)
        st.dataframe(
            df_boq,
            use_container_width=True,
            hide_index=True,
            column_config={
                "desc": _("الوصف", "Description"),
                "unit": _("الوحدة", "Unit"),
                "qty": _("الكمية", "Quantity"),
                "price": _("السعر (جنيه)", "Price (EGP)")
            }
        )
        st.markdown(f"### 💰 {_('الإجمالي التقديري', 'Estimated Total')}: **{data['boq']['total_cost']:,.2f} {_('جنيه', 'EGP')}**")
        
        col_exp1, col_exp2 = st.columns([1, 5])
        with col_exp1:
            if st.button(_("📥 تصدير Excel", "📥 Export Excel")):
                try:
                    excel_url = f"{BACKEND}/export_boq/{st.session_state.selected_project}"
                    response = requests.get(excel_url, headers=get_headers())
                    if response.status_code == 200:
                        st.download_button(
                            label=_("⬇️ تحميل Excel", "⬇️ Download Excel"),
                            data=response.content,
                            file_name=f"boq_{st.session_state.selected_project}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error(f"❌ فشل التحميل: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ خطأ: {str(e)}")
        
        with st.expander(_("🛠 إدارة البنود (حذف)", "🛠 Manage Items (Delete)")):
            for item in boq_items:
                cols = st.columns([4, 1, 1, 1])
                with cols[0]:
                    st.write(f"**{item['desc']}**")
                with cols[1]:
                    st.write(f"{item['qty']} {item['unit']}")
                with cols[2]:
                    st.write(f"{item['price']} جنيه")
                with cols[3]:
                    if st.button(_("🗑️", "🗑️"), key=f"del_boq_{item['id']}"):
                        try:
                            r = requests.delete(
                                f"{BACKEND}/boq/{item['id']}",
                                headers=get_headers()
                            )
                            if r.ok:
                                st.success(_("✅ تم الحذف", "✅ Deleted"))
                                st.rerun()
                        except:
                            st.error(_("❌ فشل", "❌ Failed"))
    else:
        st.info(_("📭 لا توجد كميات محصورة بعد.", "📭 No BOQ items yet."))
    
    with st.expander(_("➕ إضافة بند حصر يدوي", "➕ Add Manual BOQ Item")):
        with st.form("manual_boq_form"):
            desc = st.text_input(_("الوصف", "Description"))
            unit = st.selectbox(_("الوحدة", "Unit"), ["م3", "طن", "م2", "عدد"])
            qty = st.number_input(_("الكمية", "Quantity"), min_value=0.0, step=0.1)
            price = st.number_input(_("السعر الإجمالي", "Total Price"), min_value=0.0, step=100.0)
            if st.form_submit_button(_("💾 إضافة", "💾 Add")):
                if desc:
                    try:
                        r = requests.post(
                            f"{BACKEND}/add_boq/{project_id}",
                            params={"desc": desc, "unit": unit, "qty": qty, "price": price},
                            headers=get_headers()
                        )
                        if r.ok:
                            st.success(_("✅ تمت الإضافة", "✅ Added"))
                            st.rerun()
                        else:
                            st.error(f"❌ فشل الإضافة: {r.status_code}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")

# ========== العيوب (مع زر مشاركة واتساب) ==========
with tabs[3]:
    st.subheader(_("🔎 إدارة العيوب", "🔎 Defects Management"))
    
    defects = data.get('defects', [])
    
    # زر إضافة عيب جديد
    with st.expander(_("➕ إضافة عيب جديد", "➕ Add New Defect"), expanded=False):
        with st.form("add_defect_form"):
            new_desc = st.text_area(_("وصف العيب", "Defect Description"))
            new_sev = st.selectbox(_("الشدة", "Severity"), ["High", "Medium", "Low"])
            new_stat = st.selectbox(_("الحالة", "Status"), ["Open", "Resolved"])
            if st.form_submit_button(_("💾 إضافة", "💾 Add")):
                if new_desc:
                    try:
                        r = requests.post(
                            f"{BACKEND}/add_defect/{project_id}",
                            params={
                                "description": new_desc,
                                "severity": new_sev,
                                "status": new_stat
                            },
                            headers=get_headers()
                        )
                        if r.ok:
                            st.success(_("✅ تمت الإضافة", "✅ Added"))
                            st.rerun()
                        else:
                            st.error(f"❌ فشل الإضافة: {r.status_code}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")
                else:
                    st.warning(_("الرجاء إدخال وصف العيب", "Please enter defect description"))
    
    if defects:
        # أزرار فلترة
        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1:
            filter_status = st.selectbox(_("فلترة حسب الحالة", "Filter by Status"), ["الكل", "Open", "Resolved"])
        with colf2:
            filter_severity = st.selectbox(_("فلترة حسب الشدة", "Filter by Severity"), ["الكل", "High", "Medium", "Low"])
        with colf3:
            search_term = st.text_input(_("بحث في الوصف", "Search in description"))
        with colf4:
            if st.button(_("📥 تصدير التقرير", "📥 Export Report")):
                report_lines = ["تقرير العيوب", "="*30]
                for d in defects:
                    report_lines.append(f"- {d['desc']} | {d['severity']} | {d['status']}")
                report_text = "\n".join(report_lines)
                st.download_button(
                    label=_("⬇️ تحميل التقرير", "⬇️ Download Report"),
                    data=report_text,
                    file_name=f"defects_report_{project_id}.txt",
                    mime="text/plain"
                )
        
        # تطبيق الفلترة
        filtered_defects = defects
        if filter_status != "الكل":
            filtered_defects = [d for d in filtered_defects if d['status'] == filter_status]
        if filter_severity != "الكل":
            filtered_defects = [d for d in filtered_defects if d['severity'] == filter_severity]
        if search_term:
            filtered_defects = [d for d in filtered_defects if search_term.lower() in d['desc'].lower()]
        
        # عرض العيوب بعد الفلترة مع زر واتساب
        for defect in filtered_defects:
            with st.container():
                cols = st.columns([3, 1, 1, 1, 1, 1])  # عمود إضافي لواتساب
                with cols[0]:
                    st.markdown(f"**{defect['desc']}**")
                with cols[1]:
                    severity_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(defect['severity'], "⚪")
                    st.markdown(f"{severity_color} {defect['severity']}")
                with cols[2]:
                    status_icon = "✅" if defect['status'] == "Resolved" else "⏳"
                    st.markdown(f"{status_icon} {defect['status']}")
                with cols[3]:
                    with st.popover(_("✏️", "✏️")):
                        st.markdown(f"**{_('تعديل العيب', 'Edit Defect')}**")
                        new_desc = st.text_area(_("الوصف", "Description"), value=defect['desc'], key=f"desc_{defect['id']}")
                        new_sev = st.selectbox(_("الشدة", "Severity"), ["High", "Medium", "Low"], index=["High","Medium","Low"].index(defect['severity']), key=f"sev_{defect['id']}")
                        new_stat = st.selectbox(_("الحالة", "Status"), ["Open", "Resolved"], index=0 if defect['status']=="Open" else 1, key=f"stat_{defect['id']}")
                        if st.button(_("💾 حفظ", "💾 Save"), key=f"save_{defect['id']}"):
                            try:
                                r = requests.put(
                                    f"{BACKEND}/defect/{defect['id']}",
                                    params={"description": new_desc, "severity": new_sev, "status": new_stat},
                                    headers=get_headers()
                                )
                                if r.ok:
                                    st.success(_("✅ تم التحديث", "✅ Updated"))
                                    st.rerun()
                            except:
                                st.error(_("❌ فشل", "❌ Failed"))
                with cols[4]:
                    if st.button(_("🗑️", "🗑️"), key=f"del_{defect['id']}"):
                        if st.checkbox(_("تأكيد الحذف", "Confirm delete"), key=f"confirm_{defect['id']}"):
                            try:
                                r = requests.delete(
                                    f"{BACKEND}/defect/{defect['id']}",
                                    headers=get_headers()
                                )
                                if r.ok:
                                    st.success(_("✅ تم الحذف", "✅ Deleted"))
                                    st.rerun()
                            except:
                                st.error(_("❌ فشل", "❌ Failed"))
                with cols[5]:
                    # زر مشاركة عبر واتساب
                    share_text = f"عيب في مشروع {data['project_info']['name']}: {defect['desc']} (شدة: {defect['severity']})"
                    encoded_text = urllib.parse.quote(share_text)
                    wa_link = f"https://wa.me/?text={encoded_text}"
                    st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background: #25D366; color: white; border: none; border-radius: 30px; padding: 0.3rem 1rem; font-weight: 600;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
                st.markdown("---")
        
        # إحصائيات سريعة
        st.markdown("---")
        st.markdown(f"### {_('إحصائيات', 'Statistics')}")
        colst1, colst2, colst3 = st.columns(3)
        with colst1:
            st.metric(_("إجمالي العيوب", "Total Defects"), len(defects))
        with colst2:
            st.metric(_("مفتوحة", "Open"), len([d for d in defects if d['status'] == "Open"]))
        with colst3:
            st.metric(_("عالية الخطورة", "High Severity"), len([d for d in defects if d['severity'] == "High"]))
    else:
        st.info(_("✨ لا توجد عيوب مسجلة. يمكنك إضافة عيب جديد من القسم أعلاه.", "✨ No defects recorded. Add a new defect from the section above."))

# ========== الأرشيف ==========
with tabs[4]:
    st.subheader(_("📚 سجل المشروع", "📚 Project Timeline"))
    timeline = data.get('timeline', [])
    if timeline:
        for item in timeline:
            with st.expander(f"**{item.get('task')}** - {item.get('date')}"):
                st.json(item)
    else:
        st.info(_("📭 لا يوجد سجل بعد.", "📭 No timeline yet."))

# ========== تقارير الموقع (مع زر الموقع التلقائي) ==========
with tabs[5]:
    st.subheader(_("📍 تقارير الموقع", "📍 Site Reports"))
    
    # زر للحصول على الموقع الحالي (مثل واتساب)
    if st.button(_("📍 استخدم موقعي الحالي", "📍 Use my current location"), key="location_btn"):
        st.markdown("""
        <script>
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                // تخزين الإحداثيات في sessionStorage
                sessionStorage.setItem("site_lat", lat);
                sessionStorage.setItem("site_lon", lon);
                // إعادة تحميل الصفحة لملء الحقول
                window.location.reload();
            },
            (error) => {
                alert("فشل الحصول على الموقع: " + error.message);
            }
        );
        </script>
        """, unsafe_allow_html=True)
        st.info(_("جارٍ الحصول على موقعك... قد تحتاج للسماح بالوصول إلى الموقع.", "Getting your location... You may need to allow location access."))
    
    # قيم افتراضية للإحداثيات
    default_lat = 0.0
    default_lon = 0.0
    
    # التحقق من وجود إحداثيات في sessionState
    if 'site_lat' in st.session_state:
        default_lat = st.session_state.site_lat
    if 'site_lon' in st.session_state:
        default_lon = st.session_state.site_lon

    with st.expander(_("➕ إضافة تقرير جديد", "➕ Add New Report"), expanded=True):
        with st.form("site_visit_form"):
            loc_name = st.text_input(_("اسم الموقع", "Location Name"), placeholder=_("مثال: الطابق الثالث", "Example: 3rd Floor"))
            col1, col2 = st.columns(2)
            with col1:
                lat_input = st.number_input(_("خط العرض", "Latitude"), format="%.6f", value=default_lat, key="lat_input")
            with col2:
                lon_input = st.number_input(_("خط الطول", "Longitude"), format="%.6f", value=default_lon, key="lon_input")
            notes = st.text_area(_("ملاحظات", "Notes"))
            uploaded_images = st.file_uploader(
                _("صور الموقع", "Site Images"),
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="site_images"
            )
            
            if st.form_submit_button(_("💾 حفظ التقرير", "💾 Save Report")):
                files_to_send = []
                if uploaded_images:
                    for img in uploaded_images:
                        files_to_send.append(("files", (img.name, img.getvalue(), img.type)))
                
                data = {
                    "location_name": loc_name,
                    "latitude": lat_input if lat_input != 0.0 else "",
                    "longitude": lon_input if lon_input != 0.0 else "",
                    "notes": notes
                }
                
                try:
                    r = requests.post(
                        f"{BACKEND}/upload_site_visit/{project_id}",
                        data=data,
                        files=files_to_send if files_to_send else None,
                        headers=get_headers()
                    )
                    if r.ok:
                        st.success(_("✅ تم حفظ التقرير", "✅ Report saved"))
                        st.rerun()
                    else:
                        st.error(f"❌ فشل الحفظ: {r.status_code}")
                except Exception as e:
                    st.error(f"❌ خطأ: {str(e)}")
    
    st.markdown("---")
    st.subheader(_("📋 التقارير السابقة", "📋 Previous Reports"))
    
    try:
        visits_resp = requests.get(f"{BACKEND}/site_visits/{project_id}", headers=get_headers())
        if visits_resp.ok:
            visits = visits_resp.json()
            if not visits:
                st.info(_("لا توجد تقارير بعد", "No reports yet"))
            for visit in visits:
                with st.container():
                    st.markdown(f"**{visit.get('location_name', _('بدون موقع', 'No location'))}** - {visit['visit_date'][:16]}")
                    if visit.get('notes'):
                        st.caption(visit['notes'])
                    if visit.get('images'):
                        # عرض الصور كمصفوفة
                        st.image([img['path'] for img in visit['images']], width=150, caption=[img['caption'] for img in visit['images']])
                    st.markdown("---")
    except Exception as e:
        st.error(f"❌ {str(e)}")

# ========== قاعدة معرفية ==========
with tabs[6]:
    st.subheader(_("📚 القاعدة المعرفية الهندسية", "📚 Engineering Knowledge Base"))
    
    kb_options = [_("معادلات إنشائية", "Structural Formulas"),
                  _("كودات البناء", "Building Codes"),
                  _("نسب الخلط", "Mix Ratios"),
                  _("أسئلة شائعة", "FAQs")]
    choice = st.radio(_("اختر الموضوع", "Choose topic"), kb_options, horizontal=True, key="kb_radio")
    
    if choice == kb_options[0]:
        st.markdown("""
        ### معادلات إنشائية أساسية
        - **عزم الانحناء للكمرة**: M = (wL²)/8 (for simply supported)
        - **إجهاد الخرسانة**: f_c = P/A
        - **نسبة التسليح**: ρ = A_s / (b*d)
        - **طول التماسك**: L_d = (f_y * d_b) / (4 * τ_bd)
        """)
    elif choice == kb_options[1]:
        st.markdown("""
        ### الكودات الشائعة
        - **الكود المصري**: ECP 203
        - **الكود الأمريكي**: ACI 318
        - **الكود البريطاني**: BS 8110
        - **الكود الأوروبي**: Eurocode 2
        """)
    elif choice == kb_options[2]:
        st.markdown("""
        ### نسب خلط الخرسانة التقريبية (لكل متر مكعب)
        - **خرسانة عادية**: 300 كجم أسمنت + 0.8 م³ رمل + 1.2 م³ سن + ماء
        - **خرسانة مسلحة**: 350 كجم أسمنت + 0.6 م³ رمل + 1.2 م³ سن + ماء
        - **خرسانة مقاومة**: 400 كجم أسمنت + 0.5 م³ رمل + 1.1 م³ سن + إضافات
        """)
    else:
        st.markdown("""
        ### أسئلة شائعة
        - **ما هو الغطاء الخرساني؟** هي المسافة بين سطح الخرسانة وحديد التسليح.
        - **متى نستخدم كانات؟** في الكمرات والأعمدة لمقاومة القص.
        - **ما هو الفرق بين الخرسانة العادية والمسلحة؟** المسلحة تحتوي على حديد تسليح.
        """)
    
    st.markdown("---")
    st.markdown(_("🔍 **ابحث في القاعدة المعرفية**", "🔍 **Search Knowledge Base**"))
    kb_query = st.text_input(_("اكتب سؤالك هنا", "Type your question here"), key="kb_query")
    if kb_query:
        with st.spinner(_("Blue يبحث...", "Blue is searching...")):
            try:
                r = requests.post(
                    f"{BACKEND}/process",
                    data={
                        "message": kb_query,
                        "project_id": project_id,
                        "history": "[]"
                    },
                    headers=get_headers()
                )
                if r.ok:
                    res = r.json()
                    answer = res.get("results", {}).get("💻 Blue", "لم أجد إجابة")
                    st.success(answer)
                else:
                    st.error(_("❌ فشل الاتصال", "❌ Connection failed"))
            except Exception as e:
                st.error(f"⚠️ {str(e)}")
