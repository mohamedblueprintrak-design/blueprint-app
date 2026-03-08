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

# =========================================================
# BluePrint Engineering Consultancy - AI-Powered Engineering OS
# الواجهة النهائية - BluePrint Light Edition (أزرق فاتح مهني)
# =========================================================

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
BACKEND = "https://blueprint-app-jrwp.onrender.com" # عدّل الرابط حسب نشرتك

# تهيئة session state
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None
if "language" not in st.session_state:
    st.session_state.language = "ar"
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
    return text_ar if st.session_state.language == "ar" else text_en

def get_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def get_health_color(score):
    if score >= 70: return "#22c55e" # أخضر
    elif score >= 40: return "#eab308" # أصفر
    else: return "#ef4444" # أحمر

# --- CSS مخصص: تصميم BluePrint Premium Light (تعديل الألوان فقط) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');

    /* تحسين الخلفية العامة */
    .stApp {
        background-color: #f0f7ff; 
        background-image: radial-gradient(#d1e9ff 0.5px, transparent 0.5px);
        background-size: 20px 20px;
    }

    /* تصميم البطاقات (Glassmorphism Light) */
    .bp-card {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #cce3f5;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 48, 96, 0.05);
        margin-bottom: 20px;
        transition: transform 0.2s ease;
    }
    .bp-card:hover {
        transform: translateY(-3px);
        border-color: #0ea5e9;
        box-shadow: 0 8px 20px rgba(14, 165, 233, 0.12);
    }

    /* الهيدر والعناوين */
    .bp-header {
        color: #034d92;
        font-weight: 800;
        letter-spacing: -1px;
    }

    /* الأزرار الهندسية */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background: #0b2b4f;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3);
    }

    /* التبويبات المودرن */
    .stTabs [data-baseweb="tab-list"] {
        background: #e1effe;
        padding: 8px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #1e40af;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        border-radius: 8px !important;
        color: #0ea5e9 !important;
    }

    /* تخصيص المحادثة */
    .stChatMessage {
        border-radius: 15px;
        border: 1px solid #e0f2fe;
        background: #ffffff;
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
            <circle class="circle-bg" cx="70" cy="70" r="{radius}" style="fill:none; stroke:#e2e8f0; stroke-width:8;"></circle>
            <circle class="circle-progress" cx="70" cy="70" r="{radius}" stroke="{color}" 
                stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                style="fill:none; stroke-width:8; stroke-linecap:round; transition:0.5s; transform:rotate(-90deg); transform-origin:center;"></circle>
        </svg>
        <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); font-size:1.5rem; font-weight:700; color:#0b2b4f;">{score}%</div>
    </div>
    """

# --- الشريط الجانبي ---
with st.sidebar:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("🪄")
    with col2:
        st.markdown("## BluePrint")
        st.markdown("##### Engineering Consultancy")
    st.markdown("---")
    
    col_lang, col_dark = st.columns(2)
    with col_lang:
        st.button("🇺🇸 EN" if st.session_state.language == "ar" else "🇸🇦 ع", on_click=switch_lang, key="lang_btn")
    with col_dark:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    st.markdown("---")

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
                        else: st.error(_("❌ خطأ", "❌ Error"))
                    except Exception as e: st.error(str(e))
        with tab2:
            with st.form("register_form"):
                new_u = st.text_input(_("اسم المستخدم", "Username"))
                new_e = st.text_input(_("البريد", "Email"))
                new_p = st.text_input(_("كلمة المرور", "Password"), type="password")
                new_fn = st.text_input(_("الاسم الكامل", "Full Name"))
                if st.form_submit_button(_("تسجيل", "Register")):
                    try:
                        r = requests.post(f"{BACKEND}/register", params={"username":new_u,"email":new_e,"password":new_p,"full_name":new_fn})
                        if r.ok: st.success("✅")
                        else: st.error("❌")
                    except Exception as e: st.error(str(e))
    else:
        st.markdown(f'<div class="bp-card">👤 {st.session_state.user.get("full_name")}</div>', unsafe_allow_html=True)
        if st.button(_("🚪 خروج", "Logout")):
            st.session_state.token = None
            st.rerun()

    st.markdown("---")
    with st.form("new_project"):
        name = st.text_input(_("اسم المشروع", "Project Name"))
        location = st.text_input(_("الموقع", "Location"), value="Dubai")
        if st.form_submit_button(_("🚀 إنشاء", "Create")):
            requests.post(f"{BACKEND}/create_project", params={"name": name, "location": location}, headers=get_headers())
            st.rerun()

    try:
        projs = requests.get(f"{BACKEND}/projects", headers=get_headers()).json()
        if projs:
            proj_options = {f"{p['name']}": p['id'] for p in projs}
            st.session_state.selected_project = proj_options[st.selectbox(_("المشاريع", "Projects"), list(proj_options.keys()))]
    except: pass

# --- المحتوى الرئيسي ---
if not st.session_state.token:
    st.markdown("<h1 style='text-align:center;'>BluePrint OS</h1>", unsafe_allow_html=True)
    st.stop()

if st.session_state.selected_project:
    project_id = st.session_state.selected_project
    data = requests.get(f"{BACKEND}/project_data/{project_id}", headers=get_headers()).json()
    health_score = data.get('health_score', 80)

    # Header
    st.markdown(f"""
    <div class="bp-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h1 class="bp-header">🏗️ {data['project_info']['name']}</h1>
            <div style="position:relative;">{get_health_gauge(health_score)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="bp-card">💰 {data["boq"]["total_cost"]:,.0f} EGP</div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="bp-card">⚠️ {len(data["defects"])} Defects</div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="bp-card">📊 {len(data["timeline"])} Events</div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="bp-card">📁 {data.get("files_count", 0)} Files</div>', unsafe_allow_html=True)

    # Tabs
    tabs = st.tabs([_("📊 لوحة المعلومات", "Dashboard"), _("💬 Blue Chat", "Chat"), _("📦 الحصر", "BOQ"), _("🔍 العيوب", "Defects"), _("📋 الأرشيف", "Archive")])

    with tabs[0]:
        if data['boq']['items']:
            fig = px.bar(pd.DataFrame(data['boq']['items']), x='desc', y='price', color_discrete_sequence=['#0ea5e9'])
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        for msg in st.session_state.msgs:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Ask Blue..."):
            st.session_state.msgs.append({"role": "user", "content": prompt})
            # هنا يتم استدعاء الـ Backend الخاص بك
            st.rerun()

    with tabs[2]:
        st.dataframe(pd.DataFrame(data['boq']['items']), use_container_width=True)
        if st.button("Export Excel"): pass

    with tabs[3]:
        for d in data['defects']:
            st.markdown(f'<div class="bp-card">**{d["desc"]}** | {d["severity"]}</div>', unsafe_allow_html=True)

    with tabs[4]:
        st.json(data['timeline'])

# تذييل
st.markdown("<center>BluePrint OS © 2026</center>", unsafe_allow_html=True)
