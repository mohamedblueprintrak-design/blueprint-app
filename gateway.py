import streamlit as st
import pandas as pd
import time
from datetime import datetime

# 1. الإعدادات المتقدمة للهوية
st.set_page_config(page_title="BluePrint | Premium OS", page_icon="💎", layout="wide")

# 2. محرك الجماليات (The UI Engine) - تصميم زجاجي عصري
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;700&family=Inter:wght@400;600&display=swap');

    /* تحويل المتصفح بالكامل */
    html, body, [class*="css"] { 
        font-family: 'Cairo', sans-serif; 
        color: #1e293b;
        direction: rtl;
    }
    
    .stApp {
        background: radial-gradient(circle at top right, #e0f2fe, #f8fafc);
    }

    /* إخفاء شريط ستريمليت العلوي */
    header {visibility: hidden;}

    /* تصميم البطاقات الزجاجية - Glassmorphism */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 24px;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        margin-bottom: 20px;
        transition: 0.4s ease-in-out;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(14, 165, 233, 0.15);
        border-right: 10px solid #0369a1;
    }

    /* الهيدر الرئيسي الفخم */
    .hero-section {
        background: linear-gradient(135deg, #0b213f 0%, #0077be 100%);
        padding: 40px;
        border-radius: 30px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 20px 40px rgba(0, 119, 190, 0.2);
    }

    /* الأزرار الهندسية */
    .stButton > button {
        background: linear-gradient(90deg, #0369a1, #0ea5e9);
        color: white;
        border-radius: 15px;
        border: none;
        padding: 12px 30px;
        font-weight: 700;
        letter-spacing: 1px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background: #0b213f;
        box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3);
    }

    /* تخصيص التبويبات لتكون كأزرار تحكم */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.5);
        padding: 10px;
        border-radius: 20px;
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 12px;
        background: transparent;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #0369a1 !important;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# 3. مكونات الواجهة الذكية
def info_card(title, value, icon, trend):
    st.markdown(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 2rem;">{icon}</span>
            <span style="color: #10b981; font-weight: bold;">{trend} ↑</span>
        </div>
        <h3 style="color: #64748b; font-size: 1rem; margin-top: 10px;">{title}</h3>
        <h2 style="color: #0b213f; font-weight: 700; margin: 0;">{value}</h2>
    </div>
    """, unsafe_allow_html=True)

# 4. بناء الهيكل (The Layout)
with st.sidebar:
    st.markdown("<div style='text-align:center'><h1 style='color:#0369a1'>BluePrint</h1><p>Consultancy Gateway</p></div>", unsafe_allow_html=True)
    st.divider()
    project = st.selectbox("📁 اختيار المشروع النشط", ["برج المنارة السكني", "مجمع الفيلات الحديثة"])
    st.markdown("---")
    st.write("🛠️ **أدوات سريعة**")
    st.button("📄 تصدر تقرير PDF")
    st.button("📉 تحديث الحصر")

# الهيدر الاحترافي
st.markdown(f"""
<div class="hero-section">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin:0; font-size: 2.5rem;">أهلاً بك في BluePrint OS</h1>
            <p style="opacity: 0.9;">مشروع: {project} | حالة الموقع: نشط الآن</p>
        </div>
        <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 20px; text-align: center;">
            <span style="font-size: 0.8rem; display: block;">صحة المشروع</span>
            <span style="font-size: 2.2rem; font-weight: bold;">94%</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# صف الإحصائيات الفخمة
c1, c2, c3, c4 = st.columns(4)
with c1: info_card("التكلفة الحالية", "1.2M AED", "💎", "12%")
with c2: info_card("المهام المكتملة", "85/100", "✅", "5%")
with c3: info_card("العيوب المفتوحة", "03", "🔍", "0%")
with c4: info_card("فريق العمل", "12 مهندس", "👥", "2%")

st.markdown("<br>", unsafe_allow_html=True)

# التبويبات (Tabs) بتصميم مودرن
t1, t2, t3, t4 = st.tabs(["🤖 محرك ذكاء Blue", "📊 الحصر الرقمي", "🚧 متابعة التنفيذ", "⚙️ الإدارة"])

with t1:
    col_chat, col_img = st.columns([2, 1])
    with col_chat:
        st.markdown("<div class='glass-card'><h4>💬 استشارة هندسية فورية</h4></div>", unsafe_allow_html=True)
        if prompt := st.chat_input("اسأل عن تفاصيل الكود أو المواصفات..."):
            with st.chat_message("user"): st.write(prompt)
            with st.chat_message("assistant"): st.write("بناءً على مخططات المشروع والبيانات المرفوعة، يفضل البدء في صب القواعد...")
    with col_img:
        st.markdown("<div class='glass-card'><h4>🖼️ رؤية الموقع</h4><p style='font-size:0.8rem'>آخر صورة من الكاميرات</p></div>", unsafe_allow_html=True)
        st.image("https://images.unsplash.com/photo-1541888946425-d81bb19480c5?auto=format&fit=crop&w=400", use_container_width=True)

with t2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("📋 جدول الكميات الذكي (BOQ)")
    df = pd.DataFrame({
        "البند": ["خرسانة أساسات", "حديد تسليح عالي المقاومة", "عزل بيتومين"],
        "الكمية": [200, 35, 550],
        "الحالة": ["مكتمل", "جاري التوريد", "مخطط"]
    })
    st.table(df)
    st.markdown("</div>", unsafe_allow_html=True)

# تذييل الصفحة
st.markdown("<div style='text-align: center; color: #94a3b8; padding: 20px;'>BluePrint Engineering OS | Powered by AI | 2026</div>", unsafe_allow_html=True)
