import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import os
import urllib.parse

# 1. إعدادات النظام والهوية (Theme Configuration)
st.set_page_config(
    page_title="BluePrint | AI Engineering OS",
    page_icon="🪄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. الواجهة الرسومية الموحدة (Integrated CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .stApp { background-color: #f8fafc; }
    
    /* بطاقات بلو بيرينت الاحترافية */
    .bp-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    .bp-card:hover { border-right: 8px solid #0ea5e9; transform: translateX(-5px); }
    
    /* تصميم الأزرار التفاعلية */
    .stButton > button {
        background: linear-gradient(90deg, #0b2b4f, #0ea5e9);
        color: white; border-radius: 30px; border: none;
        font-weight: 600; width: 100%; transition: 0.2s;
    }
    .stButton > button:hover { box-shadow: 0 4px 12px rgba(14, 165, 233, 0.4); }

    /* هيدر الصفحة */
    .bp-header { color: #0b2b4f; font-weight: 700; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# 3. الدوال التشغيلية (Logic & API)
BACKEND = "https://blueprint-app-jrwp.onrender.com"

if "msgs" not in st.session_state: st.session_state.msgs = []
if "token" not in st.session_state: st.session_state.token = None

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def draw_gauge(score):
    color = "#22c55e" if score >= 70 else "#eab308" if score >= 40 else "#ef4444"
    st.markdown(f"""
    <div style="text-align: center; background: white; padding: 20px; border-radius: 20px; border: 1px solid #e2e8f0;">
        <p style="color: #64748b; margin:0;">حالة المشروع</p>
        <h1 style="color: {color}; font-size: 3.5rem; margin:0;">{score}%</h1>
        <div style="width: 100%; background: #f1f5f9; height: 12px; border-radius: 10px; margin-top: 10px;">
            <div style="width: {score}%; background: {color}; height: 12px; border-radius: 10px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 4. القائمة الجانبية (Sidebar Control Center)
with st.sidebar:
    st.markdown("<h2 style='color: #0b2b4f;'>🪄 BluePrint OS</h2>", unsafe_allow_html=True)
    st.caption("نظام الإدارة الهندسية الذكي")
    st.divider()

    if not st.session_state.token:
        with st.form("login"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول"):
                # منطق تسجيل الدخول هنا
                st.session_state.token = "demo_token"
                st.rerun()
    else:
        st.success("تم تسجيل الدخول: م. استشاري")
        project = st.selectbox("المشروع الحالي", ["برج النخبة - رأس الخيمة", "فيلا جميرا"])
        if st.button("🚪 خروج"):
            st.session_state.token = None
            st.rerun()

# 5. الواجهة الرئيسية (The Gateway)
if not st.session_state.token:
    st.warning("يرجى تسجيل الدخول للوصول إلى لوحة التحكم.")
    st.stop()

# رأس الصفحة
st.markdown(f"<h1 class='bp-header'>لوحة تحكم: {project}</h1>", unsafe_allow_html=True)

# صف الإحصائيات (KPIs)
col_g, col_1, col_2, col_3 = st.columns([1.2, 1, 1, 1])
with col_g: draw_gauge(82)
with col_1:
    st.markdown("<div class='bp-card'><h5>💰 الميزانية</h5><h2>4.2M</h2><small>درهم إماراتي</small></div>", unsafe_allow_html=True)
with col_2:
    st.markdown("<div class='bp-card'><h5>⚠️ العيوب</h5><h2>5</h2><small>تحتاج معالجة</small></div>", unsafe_allow_html=True)
with col_3:
    st.markdown("<div class='bp-card'><h5>📅 الجدول الزمني</h5><h2>+12</h2><small>يوم انحراف</small></div>", unsafe_allow_html=True)

# نظام التبويبات (7 Tabs)
tabs = st.tabs(["💬 ذكاء Blue", "📦 الحصر الذكي", "🔎 إدارة العيوب", "📍 تقارير الموقع", "📚 الأكواد الهندسية", "📈 التحليلات", "⚙️ الإعدادات"])

with tabs[0]: # Chat Interface
    st.markdown("### 🤖 مساعدك الهندسي الذكي")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if p := st.chat_input("اسأل Blue عن تفاصيل التصميم..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("assistant"):
            with st.spinner("جاري الرجوع للكود المصري والبريطاني..."):
                time.sleep(1)
                st.write("بناءً على المعطيات، يفضل زيادة قطر السيخ في الكانة الخارجية لضمان مقاومة القص...")

with tabs[1]: # BOQ
    st.markdown("### 📋 جدول الكميات (BOQ)")
    df = pd.DataFrame({
        "البند": ["خرسانة مسلحة", "حديد تسليح", "عزل مائي"],
        "الكمية": [250, 45, 600],
        "الوحدة": ["م3", "طن", "م2"],
        "التكلفة التقديرية": [125000, 180000, 45000]
    })
    st.dataframe(df, use_container_width=True)
    if st.button("📥 تصدير إلى Excel"): st.toast("جاري التصدير...")

with tabs[2]: # Defects
    st.markdown("### 🔍 سجل العيوب والملاحظات")
    st.error("تعشيش في العمود المحوري C2 - الطابق الأول")
    st.info("ملاحظة: تم التوجيه باستخدام Grout عالي المقاومة.")

with tabs[4]: # Engineering Codes
    st.markdown("### 📚 القاعدة المعرفية")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.write("✅ **الكود المصري (ECP 203)**: متاح للبحث")
        st.write("✅ **كود بلدية رأس الخيمة**: محدث 2026")
    with col_c2:
        st.write("✅ **AISC Steel Manual**: متاح")

# تذييل الصفحة
st.divider()
st.caption("BluePrint Gateway OS | v2.5 | Ras Al Khaimah")
