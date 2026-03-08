"""
BluePrint Engineering Consultancy - AI-Powered Engineering OS
الواجهة النهائية - BluePrint Light Edition (أزرق فاتح مهني)
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
    page_title="BluePrint | Engineering Consultancy",
    page_icon="🪄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة دعم PWA
pwa_html = """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="BluePrint">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
    <meta name="theme-color" content="#ffffff">
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# ثوابت
BACKEND = "https://blueprint-app-jrwp.onrender.com"  # عدّل الرابط حسب نشرتك

# تهيئة session state
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None
if "language" not in st.session_state:
    st.session_state.language = "ar"
if "dark_mode" not in st.session_state:  # للتبديل للوضع الليلي (اختياري)
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
    return text_ar if st.session_state.language == "ar" else text_en

def get_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

# دالة للحصول على لون Health Score
def get_health_color(score):
    if score >= 70:
        return "#22c55e"  # أخضر
    elif score >= 40:
        return "#eab308"  # أصفر
    else:
        return "#ef4444"  # أحمر

# --- CSS مخصص: تصميم BluePrint Light ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/lucide-static@0.400.0/font/lucide.css');

    /* الخلفية الرئيسية */
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
        background-image: 
            linear-gradient(rgba(14, 165, 233, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(14, 165, 233, 0.03) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #1e293b;
    }

    /* الشريط الجانبي */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f0f9ff 100%);
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.03);
    }

    /* البطاقات */
    .bp-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        transition: all 0.2s;
    }

    .bp-card:hover {
        border-color: #0ea5e9;
        box-shadow: 0 10px 15px rgba(14, 165, 233, 0.1);
        transform: translateY(-2px);
    }

    /* العناوين */
    .bp-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #0b2b4f;
        margin-bottom: 0.5rem;
    }
    
    .bp-subheader {
        color: #334155;
        font-size: 1rem;
    }

    /* مؤشر الصحة الدائري */
    .health-circle {
        position: relative;
        width: 140px;
        height: 140px;
        margin: 0 auto;
    }
    
    .health-circle svg {
        transform: rotate(-90deg);
    }
    
    .health-circle .circle-bg {
        fill: none;
        stroke: #e2e8f0;
        stroke-width: 8;
    }
    
    .health-circle .circle-progress {
        fill: none;
        stroke-width: 8;
        stroke-linecap: round;
        transition: stroke-dashoffset 0.5s ease;
    }
    
    .health-circle .percentage {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.8rem;
        font-weight: 700;
        color: #0b2b4f;
    }

    /* الأزرار */
    .stButton > button {
        background: linear-gradient(90deg, #0ea5e9, #2563eb);
        color: white;
        border: none;
        border-radius: 30px;
        padding: 0.5rem 1.8rem;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(14, 165, 233, 0.2);
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(14, 165, 233, 0.25);
    }

    /* حقول الإدخال */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 30px;
        padding: 0.75rem 1rem;
        color: #1e293b;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: #0ea5e9;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
    }

    /* المحادثة */
    .stChatMessage {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .stChatMessage [data-testid="stChatMessageAvatarAssistant"] {
        background: #0ea5e9;
    }

    /* تبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #64748b;
        font-weight: 500;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background: #ffffff;
        color: #0b2b4f;
        border-bottom: 2px solid #0ea5e9;
    }

    /* مؤشرات الأداء */
    .metric-icon {
        font-size: 1.8rem;
        color: #0ea5e9;
        margin-bottom: 0.5rem;
    }
    
    .metric-val {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0b2b4f;
        line-height: 1.2;
    }
    
    .metric-label {
        color: #64748b;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* مربعات التحميل */
    .upload-area {
        border: 2px dashed #0ea5e9;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: #ffffff;
        transition: all 0.2s;
    }
    
    .upload-area:hover {
        background: #f0f9ff;
        border-color: #2563eb;
    }

    /* تحسينات الموبايل */
    @media (max-width: 768px) {
        .chat-message {
            max-width: 90%;
        }
        .bp-header {
            font-size: 2rem;
        }
        .metric-card {
            margin-bottom: 1rem;
        }
        .stButton button {
            width: 100%;
        }
    }

    /* الوضع الليلي (اختياري) */
    .dark-mode .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
    }
    .dark-mode .bp-card {
        background: #1e293b;
        border-color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# تطبيق الوضع الليلي إذا كان مفعلاً
if st.session_state.dark_mode:
    st.markdown("""
    <style>
        .stApp {
            background-color: #0f172a;
            color: #e2e8f0;
        }
        .bp-card {
            background: #1e293b;
            border-color: #334155;
        }
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            background: #1e293b;
            border-color: #334155;
            color: #e2e8f0;
        }
        .stTabs [data-baseweb="tab"] {
            color: #94a3b8;
        }
        .stTabs [aria-selected="true"] {
            background: #1e293b;
            color: #38bdf8;
        }
    </style>
    """, unsafe_allow_html=True)

# --- HTML Component: مؤشر الصحة الدائري ---
def get_health_gauge(score):
    color = get_health_color(score)
    radius = 55
    circumference = 2 * 3.14159 * radius
    offset = circumference - (score / 100 * circumference)
    
    return f"""
    <div class="health-circle">
        <svg width="140" height="140">
            <circle class="circle-bg" cx="70" cy="70" r="{radius}"></circle>
            <circle class="circle-progress" cx="70" cy="70" r="{radius}"
                stroke="{color}"
                stroke-dasharray="{circumference}"
                stroke-dashoffset="{offset}">
            </circle>
        </svg>
        <div class="percentage">{score}%</div>
    </div>
    """
    # --- الشريط الجانبي ---
with st.sidebar:
    # الشعار والاسم
    col1, col2 = st.columns([1, 3])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=50)
        else:
            st.markdown("🪄", unsafe_allow_html=True)
    with col2:
        st.markdown("## BluePrint")
        st.markdown("##### Engineering Consultancy")
    
    st.markdown("---")
    
    # زر تبديل اللغة والوضع الليلي
    col_lang, col_dark = st.columns(2)
    with col_lang:
        st.button("🇺🇸 EN" if st.session_state.language == "ar" else "🇸🇦 ع", on_click=switch_lang, key="lang_btn", use_container_width=True)
    with col_dark:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️", key="dark_btn", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    
    st.markdown("---")
    
    # قسم المصادقة
    if not st.session_state.token:
        st.markdown(f"### {_('🔐 تسجيل الدخول', '🔐 Login')}")
        tab1, tab2 = st.tabs([_("تسجيل دخول", "Login"), _("مستخدم جديد", "Register")])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input(_("اسم المستخدم", "Username"))
                password = st.text_input(_("كلمة المرور", "Password"), type="password")
                if st.form_submit_button(_("دخول", "Login"), use_container_width=True):
                    try:
                        r = requests.post(f"{BACKEND}/token", data={"username": username, "password": password})
                        if r.ok:
                            st.session_state.token = r.json()["access_token"]
                            user_r = requests.get(f"{BACKEND}/users/me", headers=get_headers())
                            if user_r.ok:
                                st.session_state.user = user_r.json()
                                st.success(_("✅ تم", "✅ OK"))
                                st.rerun()
                            else:
                                st.error(_("❌ فشل جلب المستخدم", "❌ User fetch failed"))
                        else:
                            st.error(_("❌ اسم مستخدم أو كلمة مرور خطأ", "❌ Invalid credentials"))
                    except Exception as e:
                        st.error(f"❌ {str(e)}")
        
        with tab2:
            with st.form("register_form"):
                new_u = st.text_input(_("اسم المستخدم", "Username"))
                new_e = st.text_input(_("البريد", "Email"))
                new_p = st.text_input(_("كلمة المرور", "Password"), type="password")
                new_fn = st.text_input(_("الاسم الكامل", "Full Name"))
                if st.form_submit_button(_("تسجيل", "Register"), use_container_width=True):
                    if len(new_p) > 72:
                        st.error(_("كلمة المرور طويلة جداً", "Password too long"))
                    else:
                        try:
                            r = requests.post(f"{BACKEND}/register", params={
                                "username": new_u, "email": new_e, "password": new_p, "full_name": new_fn
                            })
                            if r.ok:
                                st.success(_("✅ تم التسجيل", "✅ Registered"))
                            else:
                                st.error(r.json().get("detail", "❌ فشل"))
                        except Exception as e:
                            st.error(str(e))
    else:
        # معلومات المستخدم
        st.markdown(f"""
        <div class="bp-card" style="margin-bottom: 1rem;">
            <p style="color: #0b2b4f; font-weight: bold; margin:0;">👤 {st.session_state.user.get('full_name', 'User')}</p>
            <small style="color: #64748b;">{st.session_state.user.get('role', 'user')}</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button(_("🚪 تسجيل خروج", "🚪 Logout"), use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.selected_project = None
            st.rerun()

        st.markdown("---")
        
        # إنشاء مشروع جديد
        st.markdown(f"### 📁 {_('مشروع جديد', 'New Project')}")
        with st.form("new_project", clear_on_submit=True):
            name = st.text_input(_("اسم المشروع", "Project Name"), placeholder=_("مثال: برج الأندلس", "Example: Andalusia Tower"))
            location = st.text_input(_("الموقع", "Location"), value="Cairo")
            if st.form_submit_button(_("🚀 إنشاء", "🚀 Create"), use_container_width=True):
                if name:
                    r = requests.post(f"{BACKEND}/create_project", params={"name": name, "location": location}, headers=get_headers())
                    if r.ok:
                        st.success(_("✅ تم الإنشاء", "✅ Created"))
                        time.sleep(1)
                        st.rerun()
        
        st.markdown("---")
        
        # اختيار مشروع موجود
        st.markdown(f"### 📂 {_('المشاريع', 'Projects')}")
        try:
            projs = requests.get(f"{BACKEND}/projects", headers=get_headers()).json()
            if projs:
                proj_options = {f"{p['name']} - {p['location']}": p['id'] for p in projs}
                selected_label = st.selectbox(_("اختر مشروع", "Select Project"), list(proj_options.keys()))
                st.session_state.selected_project = proj_options[selected_label]
            else:
                st.info(_("✨ لا توجد مشاريع", "✨ No projects"))
        except Exception as e:
            st.error(_("🔌 خطأ في الاتصال", "🔌 Connection error"))
        
        if st.session_state.selected_project:
            st.markdown("---")
            st.markdown(f"### ⚙️ {_('الإجراءات', 'Actions')}")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📄 PDF", key="btn_pdf", use_container_width=True):
                    try:
                        r = requests.get(f"{BACKEND}/export_pdf/{st.session_state.selected_project}", headers=get_headers())
                        if r.ok:
                            st.download_button(
                                label=_("⬇️ تحميل", "⬇️ Download"),
                                data=r.content,
                                file_name=f"report_{st.session_state.selected_project}.pdf",
                                mime="application/pdf"
                            )
                        else:
                            st.error(f"❌ {r.status_code}")
                    except Exception as e:
                        st.error(str(e))
            with col2:
                if st.button("📝 Word", key="btn_word", use_container_width=True):
                    try:
                        r = requests.get(f"{BACKEND}/export_word/{st.session_state.selected_project}", headers=get_headers())
                        if r.ok:
                            st.download_button(
                                label=_("⬇️ تحميل", "⬇️ Download"),
                                data=r.content,
                                file_name=f"report_{st.session_state.selected_project}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                        else:
                            st.error(f"❌ {r.status_code}")
                    except Exception as e:
                        st.error(str(e))
            with col3:
                if st.button("🗑️", key="btn_delete", use_container_width=True):
                    if st.session_state.selected_project:
                        r = requests.delete(f"{BACKEND}/project/{st.session_state.selected_project}", headers=get_headers())
                        if r.ok:
                            st.success(_("✅ تم الحذف", "✅ Deleted"))
                            st.session_state.selected_project = None
                            st.rerun()
            
            # إعدادات المشروع
            with st.expander(_("⚙️ إعدادات المشروع", "⚙️ Project Settings")):
                try:
                    settings_resp = requests.get(f"{BACKEND}/project_settings/{st.session_state.selected_project}", headers=get_headers())
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
                    new_conc = st.number_input(_("سعر الخرسانة (جنيه/م³)", "Concrete price"), value=conc_price, step=50.0)
                    new_steel = st.number_input(_("سعر الحديد (جنيه/طن)", "Steel price"), value=steel_price, step=500.0)
                    model_options = ["gemini", "gpt-4o", "deepseek", "grok", "mistral-small", "openrouter-llama32-3b", "openrouter-gemma3-4b", "openrouter-zai-glm", "huggingface-llama-3.2-3b"]
                    new_model = st.selectbox(_("النموذج المفضل", "Preferred model"), model_options, index=model_options.index(pref_model) if pref_model in model_options else 0)
                    if st.form_submit_button(_("💾 حفظ", "💾 Save")):
                        try:
                            r = requests.post(f"{BACKEND}/project_settings/{st.session_state.selected_project}",
                                              params={"concrete_price": new_conc, "steel_price": new_steel, "preferred_ai_model": new_model},
                                              headers=get_headers())
                            if r.ok:
                                st.success(_("✅ تم الحفظ", "✅ Saved"))
                        except:
                            st.error(_("❌ فشل الاتصال", "❌ Connection failed"))
            
            # إدارة قاعدة المعرفة (للمشرفين)
            if st.session_state.user.get('role') == 'admin':
                with st.expander(_("📚 إدارة المعرفة", "📚 Knowledge Base")):
                    uploaded_files = st.file_uploader(_("اختر ملفات PDF", "Choose PDFs"), type=["pdf"], accept_multiple_files=True, key="kb_uploader")
                    if uploaded_files and st.button(_("💾 رفع وفهرسة", "💾 Upload & Index")):
                        import os
                        os.makedirs("knowledge_base", exist_ok=True)
                        for f in uploaded_files:
                            with open(os.path.join("knowledge_base", f.name), "wb") as fp:
                                fp.write(f.getvalue())
                        st.success(_("✅ تم الرفع، جاري الفهرسة...", "✅ Uploaded, indexing..."))
                        from knowledge_retriever import retriever
                        retriever.index_pdfs()
                        st.success(_("✅ تمت الفهرسة", "✅ Indexed"))
                        # --- المحتوى الرئيسي ---
if not st.session_state.token:
    st.markdown(f"""
    <div style="text-align: center; padding: 5rem;">
        <h1 class="bp-header">BluePrint</h1>
        <h3 style="color: #334155; font-weight: 400;">{_('Engineering Consultancy', 'Engineering Consultancy')}</h3>
        <p style="color: #64748b; margin-top: 2rem;">{_('سجل الدخول للبدء', 'Login to start')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not st.session_state.selected_project:
    st.markdown(f"""
    <div style="text-align: center; padding: 5rem;">
        <h1 class="bp-header" style="font-size: 3rem;">👋 {_('مرحباً', 'Welcome')}</h1>
        <p style="color: #64748b;">{_('اختر مشروعاً للبدء', 'Select a project to begin')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# جلب بيانات المشروع
project_id = st.session_state.selected_project
try:
    response = requests.get(f"{BACKEND}/project_data/{project_id}", headers=get_headers())
    if response.status_code != 200:
        st.error(f"❌ خطأ من الخادم: {response.status_code}")
        st.stop()
    data = response.json()
    if "error" in data:
        st.error(data["error"])
        st.stop()
except Exception as e:
    st.error(f"❌ فشل في تحميل بيانات المشروع: {str(e)}")
    st.stop()

# استخراج Health Score
health_score = data.get('health_score', 50)

# عرض رأس المشروع مع Health Score الدائري
st.markdown(f"""
<div class="bp-card" style="margin-bottom: 2rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h1 class="bp-header" style="font-size: 2rem; margin:0;">🏗️ {data['project_info']['name']}</h1>
            <p style="color: #64748b;">📍 {data['project_info']['location']} | 🕒 {_('آخر تحديث', 'Last updated')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        <div style="text-align: center;">
            {get_health_gauge(health_score)}
            <p style="color: #64748b; font-size: 0.8rem; margin-top: -10px;">{_('صحة المشروع', 'Project Health')}</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# المؤشرات الرئيسية (4 بطاقات)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">📊</div>
        <div class="metric-val">{len(data.get('timeline', []))}</div>
        <div class="metric-label">{_('تحليلات', 'Analyses')}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    total_cost = data.get('boq', {}).get('total_cost', 0)
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">💰</div>
        <div class="metric-val">{total_cost:,.0f}</div>
        <div class="metric-label">{_('جنيه', 'EGP')}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    defects_count = len(data.get('defects', []))
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">⚠️</div>
        <div class="metric-val">{defects_count}</div>
        <div class="metric-label">{_('عيوب', 'Defects')}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    files_count = data.get('files_count', 0)
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">📁</div>
        <div class="metric-val">{files_count}</div>
        <div class="metric-label">{_('ملفات', 'Files')}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# تبويبات الواجهة (7 تبويبات كاملة)
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
    
    if data.get('boq', {}).get('items'):
        df = pd.DataFrame(data['boq']['items'])
        fig = px.bar(df, x='desc', y='price', 
                     title=_('تكلفة بنود الحصر', 'BOQ Items Cost'),
                     labels={'desc': _('البند', 'Item'), 'price': _('السعر (جنيه)', 'Price (EGP)')},
                     color_discrete_sequence=['#0ea5e9'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_family='Cairo',
            title_font_size=20,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(_("📉 لا توجد بيانات حصر كافية لإنشاء رسم بياني", "📉 No BOQ data"))
        # ========== المحادثة مع Blue (مع رفع الملفات) ==========
with tabs[1]:
    st.markdown(f"## {_('💬 التحدث مع Blue', '💬 Chat with Blue')}")
    
    for msg in st.session_state.msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    with st.expander(_("📎 رفع ملفات للتحليل", "📎 Upload files for analysis")):
        uploaded_files = st.file_uploader(
            _("اختر صور أو ملفات PDF", "Choose images or PDF files"),
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="chat_uploader"
        )
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} {_('ملف', 'file(s)')}")
    
    prompt = st.chat_input(_("اكتب طلبك هنا...", "Type your message..."), key="chat_main")
    
    if prompt or uploaded_files:
        if prompt:
            st.session_state.msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner(_("Blue يفكر...", "Blue is thinking...")):
                try:
                    files = []
                    if uploaded_files:
                        for f in uploaded_files:
                            files.append(("files", (f.name, f.getvalue(), f.type)))
                    else:
                        files = None
                    
                    data_payload = {
                        "message": prompt or "",
                        "project_id": project_id,
                        "history": json.dumps(st.session_state.msgs[:-1] if prompt else st.session_state.msgs)
                    }
                    
                    response = requests.post(f"{BACKEND}/process", data=data_payload, files=files, headers=get_headers(), timeout=30)
                    
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
        st.dataframe(df_boq, use_container_width=True, hide_index=True,
                     column_config={"desc": _("الوصف", "Description"),
                                    "unit": _("الوحدة", "Unit"),
                                    "qty": _("الكمية", "Quantity"),
                                    "price": _("السعر (جنيه)", "Price (EGP)")})
        st.markdown(f"### 💰 {_('الإجمالي التقديري', 'Estimated Total')}: **{data['boq']['total_cost']:,.2f} {_('جنيه', 'EGP')}**")
        
        col_exp1, col_exp2 = st.columns([1, 5])
        with col_exp1:
            if st.button(_("📥 تصدير Excel", "📥 Export Excel")):
                try:
                    excel_url = f"{BACKEND}/export_boq/{st.session_state.selected_project}"
                    r = requests.get(excel_url, headers=get_headers())
                    if r.ok:
                        st.download_button(label=_("⬇️ تحميل", "⬇️ Download"), data=r.content,
                                           file_name=f"boq_{st.session_state.selected_project}.xlsx",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.error(f"❌ فشل التحميل: {r.status_code}")
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
                            r = requests.delete(f"{BACKEND}/boq/{item['id']}", headers=get_headers())
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
                        r = requests.post(f"{BACKEND}/add_boq/{project_id}", params={"desc": desc, "unit": unit, "qty": qty, "price": price}, headers=get_headers())
                        if r.ok:
                            st.success(_("✅ تمت الإضافة", "✅ Added"))
                            st.rerun()
                        else:
                            st.error(f"❌ فشل الإضافة: {r.status_code}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")
                        # ========== العيوب ==========
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
                        r = requests.post(f"{BACKEND}/add_defect/{project_id}", params={"description": new_desc, "severity": new_sev, "status": new_stat}, headers=get_headers())
                        if r.ok:
                            st.success(_("✅ تمت الإضافة", "✅ Added"))
                            st.rerun()
                        else:
                            st.error(f"❌ فشل الإضافة: {r.status_code}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")
                else:
                    st.warning(_("الرجاء إدخال وصف العيب", "Please enter description"))
    
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
                st.download_button(label=_("⬇️ تحميل", "⬇️ Download"), data=report_text, file_name=f"defects_{project_id}.txt", mime="text/plain")
        
        # تطبيق الفلترة
        filtered_defects = defects
        if filter_status != "الكل":
            filtered_defects = [d for d in filtered_defects if d['status'] == filter_status]
        if filter_severity != "الكل":
            filtered_defects = [d for d in filtered_defects if d['severity'] == filter_severity]
        if search_term:
            filtered_defects = [d for d in filtered_defects if search_term.lower() in d['desc'].lower()]
        
        # عرض العيوب
        for defect in filtered_defects:
            with st.container():
                cols = st.columns([3, 1, 1, 1, 1, 1])
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
                                r = requests.put(f"{BACKEND}/defect/{defect['id']}", params={"description": new_desc, "severity": new_sev, "status": new_stat}, headers=get_headers())
                                if r.ok:
                                    st.success(_("✅ تم التحديث", "✅ Updated"))
                                    st.rerun()
                            except:
                                st.error(_("❌ فشل", "❌ Failed"))
                with cols[4]:
                    if st.button(_("🗑️", "🗑️"), key=f"del_{defect['id']}"):
                        if st.checkbox(_("تأكيد الحذف", "Confirm delete"), key=f"confirm_{defect['id']}"):
                            try:
                                r = requests.delete(f"{BACKEND}/defect/{defect['id']}", headers=get_headers())
                                if r.ok:
                                    st.success(_("✅ تم الحذف", "✅ Deleted"))
                                    st.rerun()
                            except:
                                st.error(_("❌ فشل", "❌ Failed"))
                with cols[5]:
                    share_text = f"عيب في مشروع {data['project_info']['name']}: {defect['desc']} (شدة: {defect['severity']})"
                    encoded_text = urllib.parse.quote(share_text)
                    wa_link = f"https://wa.me/?text={encoded_text}"
                    st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background: #25D366; color: white; border: none; border-radius: 30px; padding: 0.3rem 1rem; font-weight: 600;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
                st.markdown("---")
        
        # إحصائيات
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
        st.info(_("✨ لا توجد عيوب مسجلة.", "✨ No defects recorded."))
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

# ========== تقارير الموقع ==========
with tabs[5]:
    st.subheader(_("📍 تقارير الموقع", "📍 Site Reports"))
    
    if st.button(_("📍 استخدم موقعي الحالي", "📍 Use my current location"), key="location_btn"):
        st.markdown("""
        <script>
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                sessionStorage.setItem("site_lat", lat);
                sessionStorage.setItem("site_lon", lon);
                window.location.reload();
            },
            (error) => {
                alert("فشل الحصول على الموقع: " + error.message);
            }
        );
        </script>
        """, unsafe_allow_html=True)
        st.info(_("جارٍ الحصول على موقعك... قد تحتاج للسماح بالوصول.", "Getting location..."))
    
    default_lat = 0.0
    default_lon = 0.0
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
            uploaded_images = st.file_uploader(_("صور الموقع", "Site Images"), type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="site_images")
            
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
                    r = requests.post(f"{BACKEND}/upload_site_visit/{project_id}", data=data, files=files_to_send if files_to_send else None, headers=get_headers())
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
        - **عزم الانحناء للكمرة**: M = (wL²)/8
        - **إجهاد الخرسانة**: f_c = P/A
        - **نسبة التسليح**: ρ = A_s / (b*d)
        """)
    elif choice == kb_options[1]:
        st.markdown("### الكودات الشائعة\n- الكود المصري: ECP 203\n- الكود الأمريكي: ACI 318\n- الكود البريطاني: BS 8110")
    elif choice == kb_options[2]:
        st.markdown("""
        ### نسب خلط الخرسانة التقريبية (لكل متر مكعب)
        - **خرسانة عادية**: 300 كجم أسمنت + 0.8 م³ رمل + 1.2 م³ سن
        - **خرسانة مسلحة**: 350 كجم أسمنت + 0.6 م³ رمل + 1.2 م³ سن
        """)
    else:
        st.markdown("""
        ### أسئلة شائعة
        - **ما هو الغطاء الخرساني؟** المسافة بين سطح الخرسانة وحديد التسليح.
        - **متى نستخدم كانات؟** في الكمرات والأعمدة لمقاومة القص.
        """)
    
    st.markdown("---")
    st.markdown(_("🔍 **ابحث في القاعدة المعرفية**", "🔍 **Search Knowledge Base**"))
    kb_query = st.text_input(_("اكتب سؤالك هنا", "Type your question here"), key="kb_query")
    if kb_query:
        with st.spinner(_("Blue يبحث...", "Blue is searching...")):
            try:
                r = requests.post(f"{BACKEND}/process", data={"message": kb_query, "project_id": project_id, "history": "[]"}, headers=get_headers())
                if r.ok:
                    res = r.json()
                    answer = res.get("results", {}).get("💻 Blue", "لم أجد إجابة")
                    st.success(answer)
                else:
                    st.error(_("❌ فشل الاتصال", "❌ Connection failed"))
            except Exception as e:
                st.error(f"⚠️ {str(e)}")
