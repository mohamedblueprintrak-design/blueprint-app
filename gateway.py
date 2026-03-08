"""
BluePrint Engineering Consultancy - AI-Powered Engineering OS
الواجهة النهائية - BluePrint Premium Edition (كامل - الجزء 1)
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
    page_title="BluePrint | Engineering OS",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. التصميم الجمالي (BluePrint Premium Theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap');

    /* الجسم العام */
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    .stApp {
        background-color: #0b2b4f; /* أزرق دارك كلاسيكي */
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        color: #e2e8f0;
    }

    /* الشريط الجانبي */
    [data-testid="stSidebar"] {
        background: #ffffff; /* خلفية بيضاء */
        border-right: 1px solid #e2e8f0;
    }
    
    [data-testid="stSidebar"] * {
        color: #1e293b !important; /* نصوص داكنة */
    }
    
    [data-testid="stSidebar"] .stButton>button {
        background: #f1f5f9;
        color: #0b2b4f !important;
        border: 1px solid #cbd5e1;
    }
    
    [data-testid="stSidebar"] .stButton>button:hover {
        background: #0b2b4f;
        color: white !important;
        border-color: #0b2b4f;
    }

    /* البطاقات */
    .bp-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        margin-bottom: 1rem;
    }

    .bp-header {
        font-size: 2.2rem;
        font-weight: 900;
        background: linear-gradient(90deg, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    /* مؤشر الصحة */
    .health-circle {
        position: relative;
        width: 140px; height: 140px; margin: 0 auto;
    }
    .health-circle svg { transform: rotate(-90deg); }
    .health-circle .circle-bg { fill: none; stroke: #334155; stroke-width: 12; }
    .health-circle .circle-progress { fill: none; stroke-width: 12; stroke-linecap: round; }
    .health-circle .percentage {
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
        font-size: 2rem; font-weight: 900; color: #ffffff;
    }

    /* الأزرار (المحتوى الرئيسي) */
    .stButton>button {
        background: linear-gradient(90deg, #0b2b4f, #1e40af);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 700;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #f59e0b, #d97706); /* ذهبي */
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
    }

    /* الحقول */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background: #1e293b !important;
        border: 1px solid #475569 !important;
        color: white !important;
        border-radius: 8px;
    }
    
    /* التبويبات */
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #f59e0b !important; /* ذهبي */
        border-bottom: 2px solid #f59e0b;
    }
    
    /* المحادثة */
    .stChatMessage {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ثوابت
BACKEND = "https://blueprint-app-jrwp.onrender.com"  # عدّل الرابط

# تهيئة session state
if "msgs" not in st.session_state: st.session_state.msgs = []
if "selected_project" not in st.session_state: st.session_state.selected_project = None
if "language" not in st.session_state: st.session_state.language = "ar"
if "token" not in st.session_state: st.session_state.token = None
if "user" not in st.session_state: st.session_state.user = None

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
    if score >= 70: return "#22c55e"
    elif score >= 40: return "#eab308"
    else: return "#ef4444"

def get_health_gauge(score):
    color = get_health_color(score)
    radius = 60
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

# --- الشريط الجانبي (Sidebar) ---
with st.sidebar:
    # 1. اللوجو
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    else:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-size: 3rem; color: #0b2b4f;">🧩</h1>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem; margin-top: -10px;">
        <h1 style="font-size: 1.5rem; color: #0b2b4f; font-weight: 900;">BluePrint</h1>
        <p style="color: #64748b; font-size: 0.85rem;">Engineering OS v9.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.button("🇺🇸 EN" if st.session_state.language == "ar" else "🇸🇦 ع", on_click=switch_lang, key="lang_btn")
    st.markdown("---")
    
    # 2. المصادقة
    if not st.session_state.token:
        with st.expander(_("🔐 تسجيل الدخول", "🔐 Login"), expanded=True):
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
                                st.rerun()
                        else: st.error(_("❌ خطأ في البيانات", "❌ Error"))
                    except: st.error(_("❌ لا يوجد اتصال", "❌ No Connection"))
        
        with st.expander(_("➕ مستخدم جديد", "➕ Register")):
            with st.form("register_form"):
                new_u = st.text_input(_("اسم المستخدم", "Username"))
                new_e = st.text_input(_("البريد", "Email"))
                new_p = st.text_input(_("كلمة المرور", "Password"), type="password")
                new_fn = st.text_input(_("الاسم الكامل", "Full Name"))
                if st.form_submit_button(_("تسجيل", "Register")):
                    if len(new_p) > 72: st.error(_("كلمة المرور طويلة", "Password too long"))
                    else:
                        try:
                            r = requests.post(f"{BACKEND}/register", params={"username": new_u, "email": new_e, "password": new_p, "full_name": new_fn})
                            if r.ok: st.success(_("✅ تم التسجيل", "✅ Registered"))
                            else: st.error(r.json().get("detail", "Error"))
                        except: st.error(_("خطأ اتصال", "Conn Error"))
    else:
        # 3. معلومات المستخدم والمشاريع
        st.markdown(f"""
        <div class="bp-card" style="background: #f1f5f9; border: 1px solid #e2e8f0; margin-bottom: 1rem;">
            <p style="color: #0b2b4f; font-weight: bold; margin:0;">👤 {st.session_state.user.get('full_name')}</p>
            <small style="color: #64748b;">{st.session_state.user.get('role')}</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button(_("🚪 تسجيل خروج", "🚪 Logout"), use_container_width=True):
            st.session_state.token = None; st.session_state.user = None; st.session_state.selected_project = None
            st.rerun()

        st.markdown("---")
        
        # إنشاء مشروع
        with st.expander(_("📁 مشروع جديد", "📁 New Project")):
            with st.form("new_project"):
                name = st.text_input(_("الاسم", "Name"))
                location = st.text_input(_("الموقع", "Location"), value="Cairo")
                if st.form_submit_button(_("إنشاء", "Create")):
                    if name:
                        requests.post(f"{BACKEND}/create_project", params={"name": name, "location": location}, headers=get_headers())
                        st.success(_("✅ تم", "✅ Done")); st.rerun()

        # اختيار مشروع
        st.markdown(f"### 📂 {_('المشاريع', 'Projects')}")
        try:
            projs = requests.get(f"{BACKEND}/projects", headers=get_headers()).json()
            if projs:
                opts = {f"{p['name']} ({p['location']})": p['id'] for p in projs}
                sel = st.selectbox(_("اختر", "Select"), list(opts.keys()))
                st.session_state.selected_project = opts[sel]
            else: st.info(_("لا توجد مشاريع", "No Projects"))
        except: st.error(_("خطأ اتصال", "Conn Error"))

        if st.session_state.selected_project:
            st.markdown("---")
            # إجراءات
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("📄 PDF", key="btn_pdf"):
                    r = requests.get(f"{BACKEND}/export_pdf/{st.session_state.selected_project}", headers=get_headers())
                    if r.ok: st.download_button("⬇️ PDF", r.content, "report.pdf")
            with c2:
                if st.button("📝 Word", key="btn_word"):
                    r = requests.get(f"{BACKEND}/export_word/{st.session_state.selected_project}", headers=get_headers())
                    if r.ok: st.download_button("⬇️ Word", r.content, "report.docx")
            with c3:
                if st.button("🗑️", key="btn_del"):
                    requests.delete(f"{BACKEND}/project/{st.session_state.selected_project}", headers=get_headers())
                    st.session_state.selected_project = None; st.rerun()
            
            # إعدادات
            with st.expander(_("⚙️ إعدادات", "⚙️ Settings")):
                try:
                    s_res = requests.get(f"{BACKEND}/project_settings/{st.session_state.selected_project}", headers=get_headers())
                    sett = s_res.json() if s_res.ok else {}
                    cp = sett.get("concrete_price", 1000.0)
                    sp = sett.get("steel_price", 35000.0)
                    am = sett.get("preferred_ai_model", "gemini")
                except: cp, sp, am = 1000.0, 35000.0, "gemini"
                
                with st.form("set_form"):
                    n_cp = st.number_input(_("سعر الخرسانة", "Conc Price"), value=cp)
                    n_sp = st.number_input(_("سعر الحديد", "Steel Price"), value=sp)
                    n_am = st.selectbox(_("النموذج", "Model"), ["gemini", "gpt-4o", "deepseek"], index=["gemini", "gpt-4o", "deepseek"].index(am))
                    if st.form_submit_button(_("حفظ", "Save")):
                        requests.post(f"{BACKEND}/project_settings/{st.session_state.selected_project}", params={"concrete_price":n_cp, "steel_price":n_sp, "preferred_ai_model":n_am}, headers=get_headers())
                        st.success(_("تم الحفظ", "Saved"))
            
            # رفع المعرفة (Admin)
            if st.session_state.user.get('role') == 'admin':
                with st.expander(_("📚 إدارة المعرفة", "📚 KB")):
                    ups = st.file_uploader(_("ملفات PDF", "PDFs"), type=["pdf"], accept_multiple_files=True)
                    if ups and st.button(_("رفع", "Upload")):
                        os.makedirs("knowledge_base", exist_ok=True)
                        for f in ups:
                            with open(os.path.join("knowledge_base", f.name), "wb") as fp: fp.write(f.getvalue())
                        st.success(_("تم الرفع", "Uploaded"))
                        # --- المحتوى الرئيسي ---
if not st.session_state.token:
    st.markdown(f"""
    <div style="text-align: center; padding: 5rem;">
        <h1 class="bp-header" style="font-size: 4rem;">BluePrint</h1>
        <h3 style="color: #64748b;">{_('نظام التشغيل الهندسي الذكي', 'Intelligent Engineering OS')}</h3>
        <p style="color: #475569; margin-top: 2rem;">{_('سجل الدخول للبدء', 'Login to start')}</p>
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

# --- رأس المشروع مع Health Score ---
st.markdown(f"""
<div class="bp-card" style="margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center;">
    <div>
        <h2 class="bp-header" style="margin:0; font-size: 2.2rem;">🏗️ {data['project_info']['name']}</h2>
        <p style="color: #94a3b8; font-size: 1rem;">📍 {data['project_info']['location']} | 🕒 {datetime.now().strftime('%Y-%m-%d')}</p>
    </div>
    <div>
        {get_health_gauge(health_score)}
        <p style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: -10px;">{_('صحة المشروع', 'Project Health')}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- بطاقات المؤشرات ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📊</div>
        <div style="font-size: 2rem; font-weight: 900; color: white;">{len(data.get('timeline', []))}</div>
        <div style="color: #94a3b8; font-size: 0.9rem; text-transform: uppercase;">{_('تحليلات', 'Analyses')}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    total_cost = data.get('boq', {}).get('total_cost', 0)
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">💰</div>
        <div style="font-size: 2rem; font-weight: 900; color: white;">{total_cost:,.0f}</div>
        <div style="color: #94a3b8; font-size: 0.9rem; text-transform: uppercase;">{_('جنيه', 'EGP')}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    defects_count = len(data.get('defects', []))
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">⚠️</div>
        <div style="font-size: 2rem; font-weight: 900; color: white;">{defects_count}</div>
        <div style="color: #94a3b8; font-size: 0.9rem; text-transform: uppercase;">{_('عيوب', 'Defects')}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    files_count = data.get('files_count', 0)
    st.markdown(f"""
    <div class="bp-card" style="text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📁</div>
        <div style="font-size: 2rem; font-weight: 900; color: white;">{files_count}</div>
        <div style="color: #94a3b8; font-size: 0.9rem; text-transform: uppercase;">{_('ملفات', 'Files')}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- التبويبات ---
tabs = st.tabs([
    _("📊 لوحة المعلومات", "📊 Dashboard"),
    _("💬 المحادثة مع Blue", "💬 Chat"),
    _("📦 الحصر (BOQ)", "📦 BOQ"),
    _("🔍 العيوب", "🔍 Defects"),
    _("📋 الأرشيف", "📋 Archive"),
    _("📍 تقارير الموقع", "📍 Site Reports"),
    _("📚 قاعدة معرفية", "📚 Knowledge Base")
])

# ========== Tab 1: Dashboard ==========
with tabs[0]:
    if data.get('boq', {}).get('items'):
        df = pd.DataFrame(data['boq']['items'])
        fig = px.bar(df, x='desc', y='price', 
                     title=_('تكلفة بنود الحصر', 'BOQ Items Cost'),
                     color_discrete_sequence=['#f59e0b'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_family='Cairo'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(_("📉 لا توجد بيانات حصر لعرضها", "📉 No BOQ data to display"))

# ========== Tab 2: Chat ==========
with tabs[1]:
    for msg in st.session_state.msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # رفع الملفات
    with st.expander(_("📎 رفع ملفات للتحليل", "📎 Upload files")):
        ups = st.file_uploader(_("صور/PDF", "Images/PDF"), type=["jpg","png","pdf"], accept_multiple_files=True, key="chat_up")
    
    if prompt := st.chat_input(_("اكتب طلبك هنا...", "Type here...")):
        st.session_state.msgs.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner(_("Blue يفكر...", "Thinking...")):
                try:
                    files = [("files", (f.name, f.getvalue(), f.type)) for f in ups] if ups else None
                    res = requests.post(f"{BACKEND}/process", 
                                        data={"message": prompt, "project_id": project_id, "history": json.dumps(st.session_state.msgs[:-1])}, 
                                        files=files, headers=get_headers())
                    if res.ok:
                        reply = res.json().get("results", {}).get("💻 Blue", "Error")
                        st.markdown(reply)
                        st.session_state.msgs.append({"role": "assistant", "content": reply})
                    else:
                        st.error(f"❌ {res.status_code}")
                except Exception as e:
                    st.error(f"❌ {str(e)}")

# ========== Tab 3: BOQ ==========
with tabs[2]:
    st.subheader(_("📋 جدول الكميات", "📋 Bill of Quantities"))
    boq_items = data.get('boq', {}).get('items', [])
    if boq_items:
        df_boq = pd.DataFrame(boq_items)
        st.dataframe(df_boq, use_container_width=True)
        
        if st.button("📥 Excel"):
            r = requests.get(f"{BACKEND}/export_boq/{project_id}", headers=get_headers())
            if r.ok: st.download_button("⬇️", r.content, "boq.xlsx")

    with st.expander(_("➕ إضافة بند", "➕ Add Item")):
        with st.form("add_boq"):
            d = st.text_input(_("الوصف", "Desc"))
            u = st.selectbox(_("الوحدة", "Unit"), ["م3", "طن", "م2"])
            q = st.number_input(_("الكمية", "Qty"), 0.0)
            p = st.number_input(_("السعر", "Price"), 0.0)
            if st.form_submit_button(_("إضافة", "Add")):
                requests.post(f"{BACKEND}/add_boq/{project_id}", params={"desc":d, "unit":u, "qty":q, "price":p}, headers=get_headers())
                st.rerun()

# ========== Tab 4: Defects ==========
with tabs[3]:
    st.subheader(_("🔎 إدارة العيوب", "🔎 Defects"))
    
    # Add Defect
    with st.expander(_("➕ إضافة عيب", "➕ Add Defect")):
        with st.form("add_def"):
            dd = st.text_area(_("الوصف", "Desc"))
            ds = st.selectbox(_("الشدة", "Sev"), ["High", "Medium", "Low"])
            dst = st.selectbox(_("الحالة", "Status"), ["Open", "Resolved"])
            if st.form_submit_button(_("إضافة", "Add")):
                requests.post(f"{BACKEND}/add_defect/{project_id}", params={"description":dd, "severity":ds, "status":dst}, headers=get_headers())
                st.rerun()
    
    # List Defects
    for d in data.get('defects', []):
        c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
        with c1:
            st.markdown(f"**{d['desc']}**")
        with c2:
            col = "🔴" if d['severity']=="High" else "🟡"
            st.write(f"{col} {d['severity']}")
        with c3:
            st.write(f"{'✅' if d['status']=='Resolved' else '⏳'} {d['status']}")
        with c4:
            # WhatsApp
            txt = f"عيب في {data['project_info']['name']}: {d['desc']}"
            link = f"https://wa.me/?text={urllib.parse.quote(txt)}"
            st.markdown(f'<a href="{link}" target="_blank"><button style="background: #25D366; color: white; border: none; padding: 5px 10px; border-radius: 5px;">📱</button></a>', unsafe_allow_html=True)
        st.markdown("---")

# ========== Tab 5: Archive ==========
with tabs[4]:
    st.subheader(_("📚 سجل المشروع", "📚 Timeline"))
    if data.get('timeline'):
        for item in data['timeline']:
            with st.expander(f"{item.get('date')} - {item.get('task')}"):
                st.json(item)
    else:
        st.info(_("لا يوجد سجل", "No timeline"))

# ========== Tab 6: Site Reports ==========
with tabs[5]:
    st.subheader(_("📍 تقارير الموقع", "📍 Site Reports"))
    
    with st.expander(_("➕ تقرير جديد", "➕ New Report"), expanded=True):
        with st.form("site_rep"):
            l1 = st.text_input(_("الموقع", "Location"))
            n1 = st.text_area(_("ملاحظات", "Notes"))
            imgs = st.file_uploader(_("صور", "Images"), accept_multiple_files=True, key="site_up")
            if st.form_submit_button(_("حفظ", "Save")):
                fs = [("files", (i.name, i.getvalue(), i.type)) for i in imgs] if imgs else None
                requests.post(f"{BACKEND}/upload_site_visit/{project_id}", data={"location_name":l1, "notes":n1, "latitude":"", "longitude":""}, files=fs, headers=get_headers())
                st.success(_("تم الحفظ", "Saved"))
                st.rerun()

# ========== Tab 7: Knowledge Base ==========
with tabs[6]:
    st.subheader(_("📚 قاعدة المعرفة", "📚 Knowledge Base"))
    st.markdown(_("ابحث عن أي معلومة هندسية أو كود:", "Search for engineering info:"))
    q = st.text_input(_("سؤالك", "Query"))
    if q:
        with st.spinner(_("بحث...", "Searching...")):
            r = requests.post(f"{BACKEND}/process", data={"message": q, "project_id": project_id, "history": "[]"}, headers=get_headers())
            if r.ok:
                ans = r.json().get("results", {}).get("💻 Blue", "لا توجد إجابة")
                st.info(ans)
