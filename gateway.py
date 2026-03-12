"""
BluePrint Engineering Consultancy - AI-Powered Engineering OS
الواجهة النهائية - جميع الوظائف + مهام المهندس + العملة + دائرة الصحة + اختبار النماذج + عرض الصور
"""

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import time
import os
import urllib.parse
import tempfile
import asyncio
import base64
from PIL import Image
import io

# استيراد مزود LLM لاستخدامه في اختبار النماذج
try:
    from llm_provider import llm
except ImportError:
    llm = None

st.set_page_config(
    page_title="BluePrint | Engineering Consultancy",
    page_icon="🪄",
    layout="wide",
    initial_sidebar_state="expanded"
)

pwa_html = """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="BluePrint">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
    <meta name="theme-color" content="#1e4a7a">
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# ========== قراءة رابط الـ Backend ==========
BACKEND = os.getenv("BACKEND_URL", "https://mohamedhuggig-blueprint-api.hf.space")

# ========== دوال مساعدة (تعريفها أولاً) ==========
def tr(text_ar, text_en):
    """ترجمة النصوص بين العربية والإنجليزية"""
    return text_ar if st.session_state.get("language", "ar") == "ar" else text_en

def get_headers():
    """إرجاع headers مع التوكن إذا كان موجوداً"""
    if st.session_state.get("token"):
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def get_health_color(score):
    """تحديد لون مؤشر الصحة حسب القيمة"""
    if score >= 70:
        return "#22c55e"
    elif score >= 40:
        return "#eab308"
    else:
        return "#ef4444"

def get_health_gauge(score):
    """إنشاء دائرة صحية باستخدام Plotly"""
    color = get_health_color(score)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': tr("صحة المشروع", "Project Health"), 
               'font': {'size': 14, 'color': 'white'}},
        number={'font': {'color': 'white'}},
        gauge={
            'axis': {'range': [0, 100], 
                     'tickwidth': 1, 
                     'tickcolor': "white",
                     'tickfont': {'color': 'white'}},
            'bar': {'color': color},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "white",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(239, 68, 68, 0.3)'},
                {'range': [40, 70], 'color': 'rgba(234, 179, 8, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(34, 197, 94, 0.3)'}
            ],
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={'color': "white", 'family': "Cairo"},
        height=200,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

def format_currency(amount):
    """تنسيق العملة مع الرمز المناسب"""
    symbols = {"EGP": "جنيه", "AED": "درهم", "SAR": "ريال", "USD": "$", "EUR": "€"}
    sym = symbols.get(st.session_state.get("currency", "EGP"), st.session_state.get("currency", "EGP"))
    amt = f"{amount:,.0f}"
    return f"{amt} {sym}" if st.session_state.get("language", "ar") == "ar" else f"{sym} {amt}"

def display_image_from_base64(base64_str):
    """عرض صورة من نص base64"""
    try:
        if base64_str and isinstance(base64_str, str):
            image_bytes = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_bytes))
            st.image(image, caption="رسم توضيحي للقطاع", use_container_width=True)
            return True
    except Exception as e:
        st.error(f"خطأ في عرض الصورة: {e}")
        return False
    return False

def safe_get_user_info():
    """دالة آمنة لاستخراج معلومات المستخدم مع دعم القاموس والكائن"""
    user = st.session_state.get('user')
    if user is None:
        return "User", "member"
    
    if isinstance(user, dict):
        full_name = user.get('full_name', 'User')
        role = user.get('role', 'member')
    else:
        full_name = getattr(user, 'full_name', 'User')
        role = getattr(user, 'role', 'member')
    
    return full_name, role

# ========== تهيئة Session State ==========
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None
if "language" not in st.session_state:
    st.session_state.language = "ar"
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "token" not in st.session_state:
    st.session_state.token = st.query_params.get("token", None)
if "user" not in st.session_state:
    st.session_state.user = None
if "currency" not in st.session_state:
    st.session_state.currency = "EGP"
if "tasks_data" not in st.session_state:
    st.session_state.tasks_data = []
if "last_project_id" not in st.session_state:
    st.session_state.last_project_id = None
if "current_section" not in st.session_state:
    st.session_state.current_section = st.query_params.get("section", tr("📊 لوحة المعلومات", "📊 Dashboard"))

# ========== CSS محسن (شامل) ==========
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    
    .stApp {
        background-color: #1e4a7a;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #ffffff;
    }

    .stApp div, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp span, 
    .stApp label, .stApp .stMarkdown, .stApp .stText, .stApp .stCaption {
        color: white !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2b4f 0%, #1e4a7a 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.3);
        color: #ffffff;
    }

    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stSelectbox select,
    [data-testid="stSidebar"] .stNumberInput input {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 30px;
        padding: 0.75rem 1rem;
    }
    
    [data-testid="stSidebar"] .stTextInput input::placeholder {
        color: #6b7280;
    }

    .stApp .stTextInput input,
    .stApp .stSelectbox select,
    .stApp .stNumberInput input {
        background: rgba(255, 255, 255, 0.9) !important;
        color: #000000 !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 30px;
        padding: 0.75rem 1rem;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: white;
        border-radius: 30px;
        padding: 0.5rem 1.8rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.3);
        border-color: #38bdf8;
    }

    .bp-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.2s;
        color: #ffffff;
    }

    .bp-card:hover {
        border-color: #38bdf8;
        box-shadow: 0 10px 25px rgba(56, 189, 248, 0.3);
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.15);
    }

    .bp-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }

    .metric-icon {
        font-size: 1.8rem;
        color: #38bdf8;
        margin-bottom: 0.5rem;
    }
    
    .metric-val {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
    }
    
    .metric-label {
        color: rgba(255, 255, 255, 0.8);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stApp .stButton > button {
        background: linear-gradient(90deg, #0ea5e9, #2563eb);
        color: white;
        border: none;
        border-radius: 30px;
        padding: 0.5rem 1.8rem;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
        transition: all 0.2s;
    }
    
    .stApp .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 15px rgba(14, 165, 233, 0.4);
    }

    .stChatMessage {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        color: white;
    }
    
    .stChatMessage [data-testid="stChatMessageAvatarAssistant"] {
        background: #0ea5e9;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 500;
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.15);
        color: #ffffff;
        border-bottom: 2px solid #38bdf8;
    }

    .stDataFrame, .stTable {
        color: white !important;
    }
    
    .stDataFrame thead tr th {
        background-color: #1e4a7a !important;
        color: white !important;
    }
    
    .stDataFrame tbody tr td {
        color: white !important;
    }

    /* التبويبات العلوية (radio) */
    .stRadio [role="radiogroup"] {
        display: flex;
        justify-content: center;
        gap: 1rem;
        background: rgba(255, 255, 255, 0.1);
        padding: 0.5rem 1rem;
        border-radius: 40px;
        margin-bottom: 1rem;
    }
    .stRadio [data-testid="stWidgetLabel"] { display: none; }

    @media (max-width: 768px) {
        .chat-message { max-width: 90%; }
        .bp-header { font-size: 2rem; }
        .metric-card { margin-bottom: 1rem; }
        .stButton button { width: 100%; }
    }

    .dark-mode .stApp { background-color: #0f172a; }
    .dark-mode .bp-card { background: #1e293b; border-color: #334155; color: #e2e8f0; }
    .dark-mode [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
</style>
""", unsafe_allow_html=True)

# تطبيق الوضع الداكن إذا كان مفعلاً
if st.session_state.dark_mode:
    st.markdown("""
    <style>
        .stApp { background-color: #0f172a; }
        .bp-card { background: #1e293b; border-color: #334155; color: #e2e8f0; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
    </style>
    """, unsafe_allow_html=True)

# ========== الشريط الجانبي ==========
with st.sidebar:
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
    
    col_lang, col_dark = st.columns(2)
    with col_lang:
        if st.button("🇺🇸 EN" if st.session_state.language == "ar" else "🇸🇦 ع", key="lang_btn", use_container_width=True):
            st.session_state.language = "en" if st.session_state.language == "ar" else "ar"
            st.rerun()
    with col_dark:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️", key="dark_btn", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    
    st.markdown("---")
    
    if not st.session_state.token:
        st.markdown(f"### {tr('🔐 تسجيل الدخول', '🔐 Login')}")
        tab1, tab2 = st.tabs([tr("تسجيل دخول", "Login"), tr("مستخدم جديد", "Register")])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input(tr("اسم المستخدم", "Username"))
                password = st.text_input(tr("كلمة المرور", "Password"), type="password")
                if st.form_submit_button(tr("دخول", "Login"), use_container_width=True):
                    try:
                        r = requests.post(f"{BACKEND}/token", data={"username": username, "password": password})
                        if r.ok:
                            data = r.json()
                            if data.get("success"):
                                token = data["data"]["access_token"]
                                st.session_state.token = token
                                st.query_params["token"] = token
                                user_r = requests.get(f"{BACKEND}/users/me", headers=get_headers())
                                if user_r.ok:
                                    st.session_state.user = user_r.json().get("data")
                                    st.success(tr("✅ تم", "✅ OK"))
                                    st.rerun()
                                else:
                                    st.error(tr("❌ فشل جلب المستخدم", "❌ User fetch failed"))
                            else:
                                error_msg = data.get("error", {}).get("message", tr("❌ خطأ", "❌ Error"))
                                st.error(f"❌ {error_msg}")
                        else:
                            st.error(f"❌ فشل الاتصال (الحالة: {r.status_code})")
                    except Exception as e:
                        st.error(str(e))
        
        with tab2:
            with st.form("register_form"):
                new_u = st.text_input(tr("اسم المستخدم", "Username"))
                new_e = st.text_input(tr("البريد", "Email"))
                new_p = st.text_input(tr("كلمة المرور", "Password"), type="password")
                new_fn = st.text_input(tr("الاسم الكامل", "Full Name"))
                if st.form_submit_button(tr("تسجيل", "Register"), use_container_width=True):
                    if len(new_p) > 72:
                        st.error(tr("كلمة المرور طويلة جداً", "Password too long"))
                    else:
                        try:
                            r = requests.post(f"{BACKEND}/register", params={
                                "username": new_u, "email": new_e, "password": new_p, "full_name": new_fn
                            })
                            if r.ok:
                                data = r.json()
                                if data.get("success"):
                                    st.success(tr("✅ تم التسجيل", "✅ Registered"))
                                else:
                                    error_msg = data.get("error", {}).get("message", tr("❌ فشل", "❌ Failed"))
                                    st.error(f"❌ {error_msg}")
                            else:
                                st.error(f"❌ فشل الاتصال (الحالة: {r.status_code})")
                        except Exception as e:
                            st.error(str(e))
    else:
        # استخدام الدالة الآمنة للحصول على معلومات المستخدم
        full_name, role = safe_get_user_info()
        
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.15); padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <p style="color: white; font-weight: bold; margin:0;">👤 {full_name}</p>
            <small style="color: rgba(255, 255, 255, 0.8);">{role}</small>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(tr("🚪 تسجيل خروج", "🚪 Logout"), use_container_width=True):
            for key in ["token", "user", "selected_project", "tasks_data"]:
                st.session_state[key] = None
            st.query_params.clear()
            st.rerun()

        st.markdown("---")
        
        st.markdown(f"### 📁 {tr('مشروع جديد', 'New Project')}")
        with st.form("new_project", clear_on_submit=True):
            name = st.text_input(tr("اسم المشروع", "Project Name"), placeholder=tr("مثال: برج الأندلس", "Example: Andalusia Tower"))
            location = st.text_input(tr("الموقع", "Location"), value="Cairo")
            if st.form_submit_button(tr("🚀 إنشاء", "🚀 Create"), use_container_width=True):
                if name:
                    r = requests.post(f"{BACKEND}/create_project", params={"name": name, "location": location}, headers=get_headers())
                    if r.ok:
                        data = r.json()
                        if data.get("success"):
                            st.success(tr("✅ تم الإنشاء", "✅ Created"))
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(data.get("error", {}).get("message", "❌ فشل"))
                    else:
                        st.error(f"❌ {r.status_code}")
        
        st.markdown("---")
        
        st.markdown(f"### 📂 {tr('المشاريع', 'Projects')}")
        try:
            r = requests.get(f"{BACKEND}/projects", headers=get_headers())
            if r.ok:
                data = r.json()
                if data.get("success"):
                    projs = data["data"]
                    if projs:
                        proj_options = {f"{p['name']} - {p['location']}": p['id'] for p in projs}
                        # تحديد المشروع الحالي في الـ Selectbox
                        current_proj_name = next((name for name, pid in proj_options.items() if pid == st.session_state.selected_project), None)
                        current_index = list(proj_options.keys()).index(current_proj_name) if current_proj_name else 0
                        
                        selected_label = st.selectbox(tr("اختر مشروع", "Select Project"), list(proj_options.keys()), index=current_index)
                        
                        if st.session_state.selected_project != proj_options[selected_label]:
                            st.session_state.selected_project = proj_options[selected_label]
                            st.session_state.last_project_id = None  # Force refresh tasks
                            st.rerun()
                    else:
                        st.info(tr("✨ لا توجد مشاريع", "✨ No projects"))
                else:
                    st.error(data.get("error", {}).get("message", "❌ خطأ"))
            else:
                st.error(f"❌ {r.status_code}")
        except Exception as e:
            st.error(tr("🔌 خطأ في الاتصال", "🔌 Connection error"))
        
        if st.session_state.selected_project:
            st.markdown("---")
            st.markdown(f"### ⚙️ {tr('الإجراءات', 'Actions')}")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📄 PDF", key="btn_pdf", use_container_width=True):
                    try:
                        r = requests.get(f"{BACKEND}/export_pdf/{st.session_state.selected_project}", headers=get_headers())
                        if r.ok:
                            st.download_button(
                                label=tr("⬇️ تحميل", "⬇️ Download"),
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
                    st.info(tr("ميزة Word قيد التطوير", "Word feature in development"))
            with col3:
                if st.button("🗑️", key="btn_delete", use_container_width=True):
                    if st.session_state.selected_project:
                        if st.checkbox(tr("تأكيد الحذف", "Confirm delete")):
                            r = requests.delete(f"{BACKEND}/project/{st.session_state.selected_project}", headers=get_headers())
                            if r.ok:
                                data = r.json()
                                if data.get("success"):
                                    st.success(tr("✅ تم الحذف", "✅ Deleted"))
                                    st.session_state.selected_project = None
                                    st.rerun()
                                else:
                                    st.error(data.get("error", {}).get("message", "❌ فشل"))
            
            with st.expander(tr("⚙️ إعدادات المشروع", "⚙️ Project Settings")):
                try:
                    settings_resp = requests.get(f"{BACKEND}/project_settings/{st.session_state.selected_project}", headers=get_headers())
                    if settings_resp.ok:
                        settings_data = settings_resp.json()
                        if settings_data.get("success"):
                            settings = settings_data["data"]
                            conc_price = settings.get("concrete_price", 1000.0)
                            steel_price = settings.get("steel_price", 35000.0)
                            pref_model = settings.get("preferred_ai_model", "gemini")
                        else:
                            conc_price, steel_price, pref_model = 1000.0, 35000.0, "gemini"
                    else:
                        conc_price, steel_price, pref_model = 1000.0, 35000.0, "gemini"
                except:
                    conc_price, steel_price, pref_model = 1000.0, 35000.0, "gemini"

                with st.form("project_settings_form"):
                    new_conc = st.number_input(tr("سعر الخرسانة (جنيه/م³)", "Concrete price"), value=conc_price, step=50.0)
                    new_steel = st.number_input(tr("سعر الحديد (جنيه/طن)", "Steel price"), value=steel_price, step=500.0)
                    
                    currency_options = ["EGP", "AED", "SAR", "USD", "EUR"]
                    currency_labels = {
                        "EGP": "🇪🇬 جنيه مصري", "AED": "🇦🇪 درهم إماراتي", "SAR": "🇸🇦 ريال سعودي",
                        "USD": "🇺🇸 دولار أمريكي", "EUR": "🇪🇺 يورو"
                    }
                    selected_currency = st.selectbox(
                        tr("العملة", "Currency"), currency_options,
                        format_func=lambda x: currency_labels.get(x, x),
                        index=currency_options.index(st.session_state.currency) if st.session_state.currency in currency_options else 0
                    )
                    
                    model_options = ["gemini", "gpt-4o", "deepseek", "grok", "mistral-small", "openrouter-llama32-3b", "openrouter-gemma3-4b", "openrouter-zai-glm", "huggingface-llama-3.2-3b"]
                    new_model = st.selectbox(tr("النموذج المفضل", "Preferred model"), model_options, index=model_options.index(pref_model) if pref_model in model_options else 0)
                    
                    if st.form_submit_button(tr("💾 حفظ", "💾 Save")):
                        st.session_state.currency = selected_currency
                        try:
                            r = requests.post(f"{BACKEND}/project_settings/{st.session_state.selected_project}",
                                              params={"concrete_price": new_conc, "steel_price": new_steel, "preferred_ai_model": new_model},
                                              headers=get_headers())
                            if r.ok:
                                data = r.json()
                                if data.get("success"):
                                    st.success(tr("✅ تم الحفظ", "✅ Saved"))
                                    st.rerun()
                                else:
                                    st.error(data.get("error", {}).get("message", "❌ فشل"))
                            else:
                                st.error(f"❌ {r.status_code}")
                        except:
                            st.error(tr("❌ فشل الاتصال", "❌ Connection failed"))

# ========== المحتوى الرئيسي ==========
if not st.session_state.token:
    st.markdown(f"""
    <div style="text-align: center; padding: 5rem;">
        <h1 class="bp-header">BluePrint</h1>
        <h3 style="color: #e2e8f0; font-weight: 400;">{tr('Engineering Consultancy', 'Engineering Consultancy')}</h3>
        <p style="color: #cbd5e1; margin-top: 2rem;">{tr('سجل الدخول للبدء', 'Login to start')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not st.session_state.selected_project:
    st.markdown(f"""
    <div style="text-align: center; padding: 5rem;">
        <h1 class="bp-header" style="font-size: 3rem;">👋 {tr('مرحباً', 'Welcome')}</h1>
        <p style="color: #cbd5e1;">{tr('اختر مشروعاً للبدء', 'Select a project to begin')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# جلب بيانات المشروع
@st.cache_data(ttl=60)
def fetch_project_data(pid, headers):
    try:
        r = requests.get(f"{BACKEND}/project_data/{pid}", headers=headers)
        if r.ok:
            data = r.json()
            if data.get("success"):
                return data["data"]
    except:
        pass
    return None

project_id = st.session_state.selected_project
data = fetch_project_data(project_id, get_headers())
if data is None:
    # بيانات تجريبية
    data = {
        "project_info": {"name": "مشروع تجريبي", "location": "القاهرة"},
        "timeline": [],
        "boq": {"items": [], "total_cost": 1250000},
        "defects": [],
        "files_count": 0,
        "health_score": 85
    }

health_score = data.get('health_score', 50)

# ========== الكارت العلوي ==========
with st.container():
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown(f"<h1 class='bp-header' style='font-size: 2rem; margin:0;'>🏗️ {data['project_info']['name']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #e2e8f0;'>📍 {data['project_info']['location']} | 🕒 {tr('آخر تحديث', 'Last updated')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)
    with col_right:
        fig = get_health_gauge(health_score)
        st.plotly_chart(fig, use_container_width=True)

# المؤشرات الأربعة
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">📊</div>
        <div class="metric-val">{len(data.get('timeline', []))}</div>
        <div class="metric-label">{tr('تحليلات', 'Analyses')}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    total_cost = data.get('boq', {}).get('total_cost', 0)
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">💰</div>
        <div class="metric-val">{format_currency(total_cost)}</div>
        <div class="metric-label">{tr('الميزانية', 'Budget')}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    defects_count = len(data.get('defects', []))
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">⚠️</div>
        <div class="metric-val">{defects_count}</div>
        <div class="metric-label">{tr('عيوب', 'Defects')}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    files_count = data.get('files_count', 0)
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div class="metric-icon">📁</div>
        <div class="metric-val">{files_count}</div>
        <div class="metric-label">{tr('ملفات', 'Files')}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ========== التبويبات العلوية ==========
tab_names = [
    tr("📊 لوحة المعلومات", "📊 Dashboard"),
    tr("💬 المحادثة مع Blue", "💬 Chat with Blue"),
    tr("📦 الحصر (BOQ)", "📦 BOQ"),
    tr("🔍 العيوب", "🔍 Defects"),
    tr("📋 الأرشيف", "📋 Archive"),
    tr("📍 تقارير الموقع", "📍 Site Reports"),
    tr("📚 قاعدة معرفية", "📚 Knowledge Base"),
    tr("📋 مهام المهندس", "📋 Tasks"),
    tr("🧪 اختبار النماذج", "🧪 Model Testing")
]

# استخدام st.radio لحفظ الحالة
current_section = st.radio(
    "",
    tab_names,
    horizontal=True,
    index=tab_names.index(st.session_state.current_section) if st.session_state.current_section in tab_names else 0,
    label_visibility="collapsed"
)

# إذا تغير القسم، قم بتحديث session_state و query params
if current_section != st.session_state.current_section:
    st.session_state.current_section = current_section
    st.query_params["section"] = current_section
    st.rerun()

st.markdown("---")

# ========== لوحة المعلومات ==========
if st.session_state.current_section == tab_names[0]:
    st.markdown(f"## {tr('📈 نظرة عامة على المشروع', '📈 Project Overview')}")
    
    if data.get('boq', {}).get('items'):
        df = pd.DataFrame(data['boq']['items'])
        fig = px.bar(df, x='desc', y='price', 
                     title=tr('تكلفة بنود الحصر', 'BOQ Items Cost'),
                     labels={'desc': tr('البند', 'Item'), 'price': tr('السعر', 'Price')},
                     color_discrete_sequence=['#38bdf8'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_family='Cairo',
            font_color='white',
            title_font_size=20,
            title_font_color='white',
            xaxis=dict(tickfont=dict(color='white')),
            yaxis=dict(tickfont=dict(color='white')),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(tr("📉 لا توجد بيانات حصر كافية لإنشاء رسم بياني", "📉 No BOQ data"))

# ========== المحادثة مع Blue ==========
elif st.session_state.current_section == tab_names[1]:
    st.markdown(f"## {tr('💬 التحدث مع Blue', '💬 Chat with Blue')}")
    
    # عرض الرسائل السابقة
    for msg in st.session_state.msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    with st.expander(tr("📎 رفع ملفات للتحليل", "📎 Upload files for analysis")):
        uploaded_files = st.file_uploader(
            tr("اختر صور أو ملفات PDF", "Choose images or PDF files"),
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="chat_uploader"
        )
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} {tr('ملف جاهز للرفع (اكتب رسالتك لتبدأ)', 'file(s) ready (type message to start)')}")
    
    # مربع الإدخال
    prompt = st.chat_input(tr("اكتب طلبك هنا...", "Type your message..."), key="chat_main")
    
    if prompt:
        # إضافة رسالة المستخدم للواجهة
        st.session_state.msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner(tr("Blue يفكر...", "Blue is thinking...")):
                try:
                    files = []
                    if uploaded_files:
                        for f in uploaded_files:
                            files.append(("files", (f.name, f.getvalue(), f.type)))
                    else:
                        files = None
                    
                    data_payload = {
                        "message": prompt,
                        "project_id": project_id,
                        "history": json.dumps(st.session_state.msgs[:-1])
                    }
                    
                    response = requests.post(f"{BACKEND}/process", data=data_payload, files=files, headers=get_headers(), timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            results_dict = result.get("data", {}).get("results", {})
                            if results_dict:
                                first_key = next(iter(results_dict.keys()))
                                first_value = results_dict[first_key]
                                reply = first_value if isinstance(first_value, str) else str(first_value)
                            else:
                                reply = tr("لم أفهم، حاول مرة أخرى.", "I didn't understand, please try again.")
                            
                            st.markdown(reply)
                            
                            if "image_data" in results_dict:
                                display_image_from_base64(results_dict["image_data"])
                            
                            st.session_state.msgs.append({"role": "assistant", "content": reply})
                        else:
                            error_msg = result.get("error", {}).get("message", "❌ خطأ")
                            st.error(error_msg)
                            st.session_state.msgs.append({"role": "assistant", "content": error_msg})
                    else:
                        error_msg = f"❌ خطأ من الخادم: {response.status_code}"
                        st.error(error_msg)
                        st.session_state.msgs.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    st.error(f"❌ فشل الاتصال: {str(e)}")
                    st.session_state.msgs.append({"role": "assistant", "content": f"⚠️ خطأ: {str(e)}"})

# ========== الحصر (BOQ) ==========
elif st.session_state.current_section == tab_names[2]:
    st.subheader(tr("📋 جدول الكميات والتكاليف", "📋 Bill of Quantities"))
    
    boq_items = data.get('boq', {}).get('items', [])
    if boq_items:
        df_boq = pd.DataFrame(boq_items)
        df_boq['price_display'] = df_boq['price'].apply(format_currency)
        st.dataframe(df_boq[['desc', 'unit', 'qty', 'price_display']],
                     use_container_width=True, hide_index=True,
                     column_config={
                         "desc": tr("الوصف", "Description"),
                         "unit": tr("الوحدة", "Unit"),
                         "qty": tr("الكمية", "Quantity"),
                         "price_display": tr("السعر", "Price")
                     })
        st.markdown(f"### 💰 {tr('الإجمالي التقديري', 'Estimated Total')}: **{format_currency(data['boq']['total_cost'])}**")
        
        col_exp1, col_exp2 = st.columns([1, 5])
        with col_exp1:
            if st.button(tr("📥 تصدير Excel", "📥 Export Excel")):
                try:
                    excel_url = f"{BACKEND}/export_boq/{st.session_state.selected_project}"
                    r = requests.get(excel_url, headers=get_headers())
                    if r.ok:
                        st.download_button(label=tr("⬇️ تحميل", "⬇️ Download"), data=r.content,
                                           file_name=f"boq_{st.session_state.selected_project}.xlsx",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.error(f"❌ فشل التحميل: {r.status_code}")
                except Exception as e:
                    st.error(f"❌ خطأ: {str(e)}")
        
        with st.expander(tr("🛠 إدارة البنود (حذف)", "🛠 Manage Items (Delete)")):
            for item in boq_items:
                cols = st.columns([4, 1, 1, 1])
                with cols[0]:
                    st.write(f"**{item['desc']}**")
                with cols[1]:
                    st.write(f"{item['qty']} {item['unit']}")
                with cols[2]:
                    st.write(format_currency(item['price']))
                with cols[3]:
                    if st.button(tr("🗑️", "🗑️"), key=f"del_boq_{item['id']}"):
                        if st.checkbox(tr("تأكيد الحذف", "Confirm delete"), key=f"confirm_{item['id']}"):
                            try:
                                r = requests.delete(f"{BACKEND}/boq/{item['id']}", headers=get_headers())
                                if r.ok:
                                    data = r.json()
                                    if data.get("success"):
                                        st.success(tr("✅ تم الحذف", "✅ Deleted"))
                                        st.rerun()
                                    else:
                                        st.error(data.get("error", {}).get("message", "❌ فشل"))
                            except:
                                st.error(tr("❌ فشل", "❌ Failed"))
    else:
        st.info(tr("📭 لا توجد كميات محصورة بعد.", "📭 No BOQ items yet."))
    
    with st.expander(tr("➕ إضافة بند حصر يدوي", "➕ Add Manual BOQ Item")):
        with st.form("manual_boq_form"):
            desc = st.text_input(tr("الوصف", "Description"))
            unit = st.selectbox(tr("الوحدة", "Unit"), ["م3", "طن", "م2", "عدد"])
            qty = st.number_input(tr("الكمية", "Quantity"), min_value=0.0, step=0.1)
            price = st.number_input(tr("السعر الإجمالي", "Total Price"), min_value=0.0, step=100.0)
            if st.form_submit_button(tr("💾 إضافة", "💾 Add")):
                if desc:
                    try:
                        r = requests.post(f"{BACKEND}/add_boq/{project_id}", params={"desc": desc, "unit": unit, "qty": qty, "price": price}, headers=get_headers())
                        if r.ok:
                            data = r.json()
                            if data.get("success"):
                                st.success(tr("✅ تمت الإضافة", "✅ Added"))
                                st.rerun()
                            else:
                                st.error(data.get("error", {}).get("message", "❌ فشل الإضافة"))
                        else:
                            st.error(f"❌ فشل الإضافة: {r.status_code}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")

# ========== العيوب ==========
elif st.session_state.current_section == tab_names[3]:
    st.subheader(tr("🔎 إدارة العيوب", "🔎 Defects Management"))
    
    defects = data.get('defects', [])
    
    with st.expander(tr("➕ إضافة عيب جديد", "➕ Add New Defect"), expanded=False):
        with st.form("add_defect_form"):
            new_desc = st.text_area(tr("وصف العيب", "Defect Description"))
            new_sev = st.selectbox(tr("الشدة", "Severity"), ["High", "Medium", "Low"])
            new_stat = st.selectbox(tr("الحالة", "Status"), ["Open", "Resolved"])
            if st.form_submit_button(tr("💾 إضافة", "💾 Add")):
                if new_desc:
                    try:
                        r = requests.post(f"{BACKEND}/add_defect/{project_id}", params={"description": new_desc, "severity": new_sev, "status": new_stat}, headers=get_headers())
                        if r.ok:
                            data = r.json()
                            if data.get("success"):
                                st.success(tr("✅ تمت الإضافة", "✅ Added"))
                                st.rerun()
                            else:
                                st.error(data.get("error", {}).get("message", "❌ فشل الإضافة"))
                        else:
                            st.error(f"❌ فشل الإضافة: {r.status_code}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")
                else:
                    st.warning(tr("الرجاء إدخال وصف العيب", "Please enter description"))
    
    if defects:
        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1:
            filter_status = st.selectbox(tr("فلترة حسب الحالة", "Filter by Status"), ["الكل", "Open", "Resolved"])
        with colf2:
            filter_severity = st.selectbox(tr("فلترة حسب الشدة", "Filter by Severity"), ["الكل", "High", "Medium", "Low"])
        with colf3:
            search_term = st.text_input(tr("بحث في الوصف", "Search in description"))
        with colf4:
            if st.button(tr("📥 تصدير التقرير", "📥 Export Report")):
                report_lines = ["تقرير العيوب", "="*30]
                for d in defects:
                    report_lines.append(f"- {d['desc']} | {d['severity']} | {d['status']}")
                report_text = "\n".join(report_lines)
                st.download_button(label=tr("⬇️ تحميل", "⬇️ Download"), data=report_text, file_name=f"defects_{project_id}.txt", mime="text/plain")
        
        filtered_defects = defects
        if filter_status != "الكل":
            filtered_defects = [d for d in filtered_defects if d['status'] == filter_status]
        if filter_severity != "الكل":
            filtered_defects = [d for d in filtered_defects if d['severity'] == filter_severity]
        if search_term:
            filtered_defects = [d for d in filtered_defects if search_term.lower() in d['desc'].lower()]
        
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
                    with st.popover(tr("✏️", "✏️")):
                        st.markdown(f"**{tr('تعديل العيب', 'Edit Defect')}**")
                        new_desc = st.text_area(tr("الوصف", "Description"), value=defect['desc'], key=f"desc_{defect['id']}")
                        new_sev = st.selectbox(tr("الشدة", "Severity"), ["High", "Medium", "Low"], index=["High","Medium","Low"].index(defect['severity']), key=f"sev_{defect['id']}")
                        new_stat = st.selectbox(tr("الحالة", "Status"), ["Open", "Resolved"], index=0 if defect['status']=="Open" else 1, key=f"stat_{defect['id']}")
                        if st.button(tr("💾 حفظ", "💾 Save"), key=f"save_{defect['id']}"):
                            try:
                                r = requests.put(f"{BACKEND}/defect/{defect['id']}", params={"description": new_desc, "severity": new_sev, "status": new_stat}, headers=get_headers())
                                if r.ok:
                                    data = r.json()
                                    if data.get("success"):
                                        st.success(tr("✅ تم التحديث", "✅ Updated"))
                                        st.rerun()
                                    else:
                                        st.error(data.get("error", {}).get("message", "❌ فشل"))
                            except:
                                st.error(tr("❌ فشل", "❌ Failed"))
                with cols[4]:
                    if st.button(tr("🗑️", "🗑️"), key=f"del_{defect['id']}"):
                        if st.checkbox(tr("تأكيد الحذف", "Confirm delete"), key=f"confirm_{defect['id']}"):
                            try:
                                r = requests.delete(f"{BACKEND}/defect/{defect['id']}", headers=get_headers())
                                if r.ok:
                                    data = r.json()
                                    if data.get("success"):
                                        st.success(tr("✅ تم الحذف", "✅ Deleted"))
                                        st.rerun()
                                    else:
                                        st.error(data.get("error", {}).get("message", "❌ فشل"))
                            except:
                                st.error(tr("❌ فشل", "❌ Failed"))
                with cols[5]:
                    share_text = f"عيب في مشروع {data['project_info']['name']}: {defect['desc']} (شدة: {defect['severity']})"
                    encoded_text = urllib.parse.quote(share_text)
                    wa_link = f"https://wa.me/?text={encoded_text}"
                    st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background: #25D366; color: white; border: none; border-radius: 30px; padding: 0.3rem 1rem; font-weight: 600;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
                st.markdown("---")
        
        st.markdown("---")
        st.markdown(f"### {tr('إحصائيات', 'Statistics')}")
        colst1, colst2, colst3 = st.columns(3)
        with colst1:
            st.metric(tr("إجمالي العيوب", "Total Defects"), len(defects))
        with colst2:
            st.metric(tr("مفتوحة", "Open"), len([d for d in defects if d['status'] == "Open"]))
        with colst3:
            st.metric(tr("عالية الخطورة", "High Severity"), len([d for d in defects if d['severity'] == "High"]))
    else:
        st.info(tr("✨ لا توجد عيوب مسجلة.", "✨ No defects recorded."))

# ========== الأرشيف ==========
elif st.session_state.current_section == tab_names[4]:
    st.subheader(tr("📚 سجل المشروع", "📚 Project Timeline"))
    timeline = data.get('timeline', [])
    if timeline:
        for item in timeline:
            with st.expander(f"**{item.get('task')}** - {item.get('date')}"):
                st.json(item)
    else:
        st.info(tr("📭 لا يوجد سجل بعد.", "📭 No timeline yet."))

# ========== تقارير الموقع ==========
elif st.session_state.current_section == tab_names[5]:
    st.subheader(tr("📍 تقارير الموقع", "📍 Site Reports"))
    
    # -------------------- قسم إنشاء التقرير اليومي PDF --------------------
    with st.expander(tr("📄 إنشاء تقرير يومي PDF", "📄 Create Daily PDF Report"), expanded=False):
        with st.form("daily_pdf_form"):
            col1, col2 = st.columns(2)
            with col1:
                report_date = st.date_input(tr("التاريخ", "Date"), value=datetime.now())
                location_name = st.text_input(tr("اسم الموقع", "Location Name"), value=tr("الطابق الأرضي", "Ground Floor"))
                weather = st.selectbox(tr("الحالة الجوية", "Weather"), ["مشمس", "غائم", "ممطر", "عاصف"])
            with col2:
                workers_count = st.number_input(tr("عدد العمال", "Workers Count"), min_value=0, value=10, step=1)
                equipment = st.text_area(tr("المعدات المستخدمة", "Equipment Used"), value="خلاطة, هزاز, طلمبة")
                notes = st.text_area(tr("ملاحظات", "Notes"), value="تم صب القواعد بنجاح")
            
            uploaded_images = st.file_uploader(tr("صور الموقع (اختياري)", "Site Images (optional)"), 
                                               type=["jpg", "jpeg", "png"], 
                                               accept_multiple_files=True, 
                                               key="daily_pdf_images")
            
            generate_clicked = st.form_submit_button(tr("📥 إنشاء التقرير", "📥 Generate Report"))
        
        # خارج الـ form: معالجة النتيجة وعرض زر التحميل والواتساب
        if generate_clicked:
            with st.spinner(tr("جاري إنشاء التقرير...", "Generating report...")):
                # حفظ الصور مؤقتاً
                temp_image_paths = []
                if uploaded_images:
                    for img in uploaded_images:
                        temp_path = os.path.join(tempfile.gettempdir(), img.name)
                        with open(temp_path, "wb") as f:
                            f.write(img.getbuffer())
                        temp_image_paths.append(temp_path)
                
                report_data = {
                    "date": report_date.strftime("%Y-%m-%d"),
                    "location_name": location_name,
                    "weather": weather,
                    "workers_count": workers_count,
                    "equipment": equipment,
                    "notes": notes,
                    "images": temp_image_paths
                }
                
                try:
                    from pdf_generator import generate_daily_report
                    pdf_bytes = generate_daily_report(project_id, report_data)
                    
                    if pdf_bytes:
                        # تخزين PDF وتاريخ التقرير في session_state
                        st.session_state["generated_pdf"] = pdf_bytes
                        st.session_state["generated_pdf_name"] = f"daily_report_{project_id}_{report_date}.pdf"
                        st.session_state["generated_pdf_date"] = report_date
                        st.success(tr("✅ تم إنشاء التقرير بنجاح", "✅ Report generated successfully"))
                    else:
                        st.error(tr("❌ فشل إنشاء التقرير", "❌ Failed to generate report"))
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # عرض أزرار التحميل والواتساب إذا كان هناك PDF في session_state
        if "generated_pdf" in st.session_state and st.session_state["generated_pdf"] is not None:
            col_dl, col_wa, _ = st.columns([1, 1, 3])
            with col_dl:
                st.download_button(
                    label=tr("⬇️ تحميل التقرير", "⬇️ Download Report"),
                    data=st.session_state["generated_pdf"],
                    file_name=st.session_state["generated_pdf_name"],
                    mime="application/pdf",
                    key="download_pdf_btn"
                )
            with col_wa:
                report_date_str = st.session_state.get("generated_pdf_date", datetime.now()).strftime("%Y-%m-%d")
                wa_text = f"تم إنشاء تقرير موقع لمشروع {data['project_info']['name']} بتاريخ {report_date_str}. يمكنك تحميله من المنصة."
                encoded_text = urllib.parse.quote(wa_text)
                wa_link = f"https://wa.me/?text={encoded_text}"
                st.link_button(tr("📱 مشاركة عبر واتساب", "📱 Share on WhatsApp"), wa_link, use_container_width=True)
            
            if st.button(tr("مسح التقرير من الذاكرة", "Clear report from memory")):
                st.session_state["generated_pdf"] = None
                st.session_state["generated_pdf_date"] = None
                st.rerun()
    
    st.markdown("---")
    
    # -------------------- زر الحصول على الموقع الحالي --------------------
    if st.button(tr("📍 استخدم موقعي الحالي", "📍 Use my current location"), key="location_btn"):
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
        st.info(tr("جارٍ الحصول على موقعك... قد تحتاج للسماح بالوصول.", "Getting location..."))
    
    default_lat = 0.0
    default_lon = 0.0
    if 'site_lat' in st.session_state:
        default_lat = st.session_state.site_lat
    if 'site_lon' in st.session_state:
        default_lon = st.session_state.site_lon

    # -------------------- نموذج إضافة زيارة موقع (تخزين في قاعدة البيانات) --------------------
    with st.expander(tr("➕ إضافة تقرير موقع جديد (للحفظ)", "➕ Add New Site Report (to save)"), expanded=True):
        with st.form("site_visit_form"):
            loc_name = st.text_input(tr("اسم الموقع", "Location Name"), placeholder=tr("مثال: الطابق الثالث", "Example: 3rd Floor"))
            col1, col2 = st.columns(2)
            with col1:
                lat_input = st.number_input(tr("خط العرض", "Latitude"), format="%.6f", value=default_lat, key="lat_input")
            with col2:
                lon_input = st.number_input(tr("خط الطول", "Longitude"), format="%.6f", value=default_lon, key="lon_input")
            notes = st.text_area(tr("ملاحظات", "Notes"))
            uploaded_images = st.file_uploader(tr("صور الموقع", "Site Images"), type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="site_images")
            
            if st.form_submit_button(tr("💾 حفظ التقرير", "💾 Save Report")):
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
                        resp_data = r.json()
                        if resp_data.get("success"):
                            st.success(tr("✅ تم حفظ التقرير", "✅ Report saved"))
                            st.rerun()
                        else:
                            st.error(resp_data.get("error", {}).get("message", "❌ فشل الحفظ"))
                    else:
                        st.error(f"❌ فشل الحفظ: {r.status_code}")
                except Exception as e:
                    st.error(f"❌ خطأ: {str(e)}")
    
    st.markdown("---")
    st.subheader(tr("📋 التقارير السابقة", "📋 Previous Reports"))
    
    try:
        visits_resp = requests.get(f"{BACKEND}/site_visits/{project_id}", headers=get_headers())
        if visits_resp.ok:
            data_visits = visits_resp.json()
            if data_visits.get("success"):
                visits = data_visits["data"]
                if not visits:
                    st.info(tr("لا توجد تقارير بعد", "No reports yet"))
                for visit in visits:
                    with st.container():
                        st.markdown(f"**{visit.get('location_name', tr('بدون موقع', 'No location'))}** - {visit['visit_date'][:16]}")
                        if visit.get('notes'):
                            st.caption(visit['notes'])
                        if visit.get('images'):
                            for img in visit['images']:
                                st.image(img['path'], width=150, caption=img.get('caption', ''))
                        st.markdown("---")
            else:
                st.error(data_visits.get("error", {}).get("message", "❌ خطأ"))
        else:
            st.error(f"❌ {visits_resp.status_code}")
    except Exception as e:
        st.error(f"❌ {str(e)}")

# ========== قاعدة معرفية ==========
elif st.session_state.current_section == tab_names[6]:
    st.subheader(tr("📚 القاعدة المعرفية الهندسية", "📚 Engineering Knowledge Base"))
    
    kb_options = [
        tr("معادلات إنشائية", "Structural Formulas"),
        tr("كودات البناء", "Building Codes"),
        tr("نسب الخلط", "Mix Ratios"),
        tr("أسئلة شائعة", "FAQs")
    ]
    choice = st.radio(tr("اختر الموضوع", "Choose topic"), kb_options, horizontal=True, key="kb_radio")
    
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
    st.markdown(tr("🔍 **ابحث في القاعدة المعرفية**", "🔍 **Search Knowledge Base**"))
    kb_query = st.text_input(tr("اكتب سؤالك هنا", "Type your question here"), key="kb_query")
    if kb_query:
        with st.spinner(tr("Blue يبحث...", "Blue is searching...")):
            try:
                r = requests.post(f"{BACKEND}/process", data={"message": kb_query, "project_id": project_id, "history": "[]"}, headers=get_headers())
                if r.ok:
                    res = r.json()
                    if res.get("success"):
                        answer = res.get("data", {}).get("results", {}).get("💻 Blue", tr("لم أجد إجابة", "No answer found"))
                        st.success(answer)
                    else:
                        st.error(res.get("error", {}).get("message", "❌ خطأ"))
                else:
                    st.error(tr("❌ فشل الاتصال", "❌ Connection failed"))
            except Exception as e:
                st.error(f"⚠️ {str(e)}")

# ========== مهام المهندس ==========
elif st.session_state.current_section == tab_names[7]:
    st.subheader(tr("📋 إدارة مهام المهندسين", "📋 Engineer Tasks"))
    
    # حالات المهمة الممكنة
    task_statuses = ["قيد الانتظار", "جاري", "منتهية"]
    
    # دالة لجلب المهام من الـ API
    def fetch_tasks():
        try:
            r = requests.get(f"{BACKEND}/tasks/{project_id}", headers=get_headers())
            if r.ok:
                data = r.json()
                if data.get("success"):
                    return data["data"]
            return []
        except:
            return []
    
    # جلب المهام عند تحميل الصفحة أو عند تغيير المشروع
    if "tasks_data" not in st.session_state or st.session_state.get("last_project_id") != project_id:
        st.session_state.tasks_data = fetch_tasks()
        st.session_state.last_project_id = project_id
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        with st.form("task_form", clear_on_submit=True):
            st.markdown("### ➕ إضافة مهمة جديدة")
            t_desc = st.text_input(tr("وصف المهمة", "Task description"), key="task_desc")
            t_ass = st.text_input(tr("اسم المهندس", "Engineer name"), key="task_ass")
            t_date = st.date_input(tr("تاريخ التسليم", "Deadline"), value=date.today(), key="task_date")
            t_prio = st.select_slider(tr("الأولوية", "Priority"), options=["منخفضة", "متوسطة", "عالية"], value="متوسطة", key="task_prio")
            t_status = st.selectbox(tr("الحالة", "Status"), task_statuses, index=0, key="task_status")
            
            submitted = st.form_submit_button(tr("➕ إضافة مهمة", "➕ Add task"))
            if submitted and t_desc and t_ass:
                try:
                    r = requests.post(
                        f"{BACKEND}/tasks/{project_id}",
                        params={
                            "description": t_desc,
                            "assignee": t_ass,
                            "due_date": t_date.strftime("%Y-%m-%d"),
                            "priority": t_prio,
                            "status": t_status
                        },
                        headers=get_headers()
                    )
                    if r.ok:
                        data = r.json()
                        if data.get("success"):
                            st.success(tr("✅ تمت الإضافة", "✅ Added"))
                            st.session_state.tasks_data = fetch_tasks()
                            st.rerun()
                        else:
                            st.error(data.get("error", {}).get("message", "❌ فشل الإضافة"))
                    else:
                        st.error(f"❌ فشل الإضافة: {r.status_code}")
                except Exception as e:
                    st.error(f"❌ خطأ: {str(e)}")
    
    with col2:
        if st.session_state.tasks_data:
            st.markdown("### 📋 قائمة المهام")
            
            for i, task in enumerate(st.session_state.tasks_data):
                cols = st.columns([3, 1, 1, 1, 1])
                with cols[0]:
                    st.write(f"**{task['description']}**")
                    st.caption(f"{task['assignee']} | أولوية: {task['priority']}")
                with cols[1]:
                    st.write(f"تسليم: {task['due_date']}")
                with cols[2]:
                    status_color = {
                        "قيد الانتظار": "🟡",
                        "جاري": "🔵",
                        "منتهية": "✅"
                    }.get(task['status'], "⚪")
                    st.write(f"{status_color} {task['status']}")
                with cols[3]:
                    if task['status'] != "منتهية":
                        next_status = "جاري" if task['status'] == "قيد الانتظار" else "منتهية"
                        if st.button(f"⏩ {next_status}", key=f"status_{task['id']}"):
                            try:
                                r = requests.put(
                                    f"{BACKEND}/tasks/{task['id']}",
                                    params={"status": next_status},
                                    headers=get_headers()
                                )
                                if r.ok:
                                    st.session_state.tasks_data = fetch_tasks()
                                    st.rerun()
                            except:
                                pass
                    else:
                        st.write("---")
                with cols[4]:
                    if st.button("🗑️", key=f"del_{task['id']}"):
                        try:
                            r = requests.delete(f"{BACKEND}/tasks/{task['id']}", headers=get_headers())
                            if r.ok:
                                st.session_state.tasks_data = fetch_tasks()
                                st.rerun()
                        except:
                            pass
                st.markdown("---")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("إجمالي المهام", len(st.session_state.tasks_data))
            with col_stat2:
                pending = sum(1 for t in st.session_state.tasks_data if t['status'] == "قيد الانتظار")
                st.metric("قيد الانتظار", pending)
            with col_stat3:
                completed = sum(1 for t in st.session_state.tasks_data if t['status'] == "منتهية")
                st.metric("منتهية", completed)
            
            if st.button(tr("🗑️ حذف المنتهية", "🗑️ Clear completed")):
                for task in st.session_state.tasks_data:
                    if task['status'] == "منتهية":
                        try:
                            requests.delete(f"{BACKEND}/tasks/{task['id']}", headers=get_headers())
                        except:
                            pass
                st.session_state.tasks_data = fetch_tasks()
                st.rerun()
        else:
            st.info(tr("لا توجد مهام. أضف مهمة جديدة من اليسار.", "No tasks. Add a new task from the left."))

# ========== اختبار النماذج ==========
elif st.session_state.current_section == tab_names[8]:
    st.subheader(tr("🧪 اختبار النماذج الذكية", "🧪 AI Models Testing"))
    
    if llm is None:
        st.warning(tr("⚠️ لم يتم العثور على ملف llm_provider.py، لن تعمل هذه الميزة", "⚠️ llm_provider.py not found, this feature won't work"))
        st.stop()
    
    st.markdown("""
    هذه الأداة تساعدك في معرفة أي من النماذج المضافة في ملف `llm_provider.py` يعمل بشكل صحيح مع مفاتيح API الحالية.
    اضغط على زر **اختبار** بجانب كل نموذج لفحصه.
    """)
    
    models_to_test = [
        "gpt-4o-mini",
        "gemini-flash",
        "gemini",
        "mistral-small",
        "mistral-medium",
        "mistral-large",
        "deepseek-free",
        "openrouter-llama32-3b",
        "openrouter-gemma3-4b",
        "openrouter-zai-glm",
        "huggingface-llama-3.2-3b",
        "huggingface-llama-3.1-8b",
        "huggingface-mistral-7b",
        "huggingface-gemma-2-2b",
        "huggingface-qwen-2.5-7b"
    ]
    
    if "model_test_results" not in st.session_state:
        st.session_state.model_test_results = {}
    
    async def test_single_model(model_name):
        prompt = "قل 'مرحباً' فقط"
        try:
            response = await llm.generate_text(prompt, model_preference=[model_name])
            if response and not response.startswith("⚠️"):
                return "✅ نعم", response[:50]
            else:
                return "❌ لا", response[:50]
        except Exception as e:
            return "❌ خطأ", str(e)[:50]
    
    for model_name in models_to_test:
        with st.container():
            cols = st.columns([2, 1, 2])
            with cols[0]:
                st.write(f"**{model_name}**")
            with cols[1]:
                if model_name in st.session_state.model_test_results:
                    result, msg = st.session_state.model_test_results[model_name]
                    if "✅" in result:
                        st.success(result)
                    else:
                        st.error(result)
                else:
                    st.write("⏳ لم يختبر بعد")
            with cols[2]:
                if st.button(tr("اختبار", "Test"), key=f"test_{model_name}"):
                    with st.spinner(f"جاري اختبار {model_name}..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result, msg = loop.run_until_complete(test_single_model(model_name))
                        loop.close()
                        st.session_state.model_test_results[model_name] = (result, msg)
                        st.rerun()
            if model_name in st.session_state.model_test_results:
                with cols[2]:
                    st.caption(st.session_state.model_test_results[model_name][1])
            st.markdown("---")
    
    if st.button(tr("🔄 إعادة تعيين الاختبارات", "🔄 Reset Tests")):
        st.session_state.model_test_results = {}
        st.rerun()

# تذييل الصفحة
st.markdown("<br><hr style='border-color:#334155;'><center style='color: #cbd5e1;'>BluePrint AI v3.0 | 2026</center>", unsafe_allow_html=True)
