import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="BluePrint Engineering OS",
    page_icon="📐",
    layout="wide"
)
st.markdown("""
<style>

.stApp{
background-color:#f8fafc;
background-image:
linear-gradient(rgba(14,165,233,0.05) 1px,transparent 1px),
linear-gradient(90deg,rgba(14,165,233,0.05) 1px,transparent 1px);
background-size:40px 40px;
}

.bp-card{
background:white;
padding:20px;
border-radius:16px;
border:1px solid #e2e8f0;
box-shadow:0 6px 20px rgba(0,0,0,0.05);
transition:all .3s;
text-align:center;
}

.bp-card:hover{
transform:translateY(-5px);
box-shadow:0 20px 40px rgba(0,0,0,0.08);
}

.metric-number{
font-size:28px;
font-weight:700;
}

.metric-label{
color:#64748b;
font-size:14px;
}

</style>
""", unsafe_allow_html=True)
st.markdown(f"""
<div style="
background: linear-gradient(135deg,#0ea5e9,#1d4ed8);
padding:30px;
border-radius:18px;
color:white;
margin-bottom:25px;
box-shadow:0 10px 25px rgba(0,0,0,0.1);
">

<h1 style="margin:0;font-size:34px;">
📐 BluePrint Engineering Consultancy
</h1>

<p style="margin-top:8px;font-size:16px;opacity:0.9">
AI Powered Engineering Operating System
</p>

</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("""
### 📂 Navigation
""")

page = st.sidebar.radio(
    "",
    [
        "Dashboard",
        "AI Assistant",
        "BOQ",
        "Defects",
        "Reports",
        "Knowledge Base"
    ]
)
def metric_card(icon,value,label,color):

    st.markdown(f"""
    <div class="bp-card">

    <div style="font-size:28px">{icon}</div>

    <div class="metric-number" style="color:{color}">
    {value}
    </div>

    <div class="metric-label">
    {label}
    </div>

    </div>
    """, unsafe_allow_html=True)
    if page == "Dashboard":

    st.subheader("📊 Project Dashboard")

    try:
        data = requests.get(f"{API_URL}/project/data").json()
    except:
        data = {}

    col1,col2,col3,col4 = st.columns(4)

    with col1:
        metric_card("📊",len(data.get("timeline",[])),"Analyses","#2563eb")

    with col2:
        metric_card("💰",data.get("cost",0),"Cost","#16a34a")

    with col3:
        metric_card("⚠️",len(data.get("defects",[])),"Defects","#ef4444")

    with col4:
        metric_card("📁",len(data.get("files",[])),"Files","#7c3aed")
        elif page == "AI Assistant":

    st.subheader("🤖 Blue AI Engineering Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Ask Blue about engineering...")

    if prompt:

        st.session_state.messages.append(
            {"role":"user","content":prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        response = requests.post(
            f"{API_URL}/chat",
            json={"question":prompt}
        ).json()

        answer = response.get("answer","No response")

        with st.chat_message("assistant"):
            st.markdown(answer)

        st.session_state.messages.append(
            {"role":"assistant","content":answer}
        )
        elif page == "BOQ":

    st.subheader("💰 Bill of Quantities")

    file = st.file_uploader("Upload BOQ Excel", type=["xlsx"])

    if file:

        df = pd.read_excel(file)

        st.dataframe(df)

        total = df["Total"].sum() if "Total" in df.columns else 0

        st.success(f"Total Cost: {total}")
        elif page == "Defects":

    st.subheader("⚠️ Site Defects")

    defect = st.text_input("Defect description")

    if st.button("Add Defect"):

        requests.post(
            f"{API_URL}/defect",
            json={"text":defect}
        )

        st.success("Defect Added")
elif page == "Reports":

    st.subheader("📝 Site Reports")

    report = st.text_area("Write report")

    if st.button("Save Report"):

        requests.post(
            f"{API_URL}/report",
            json={"text":report}
        )

        st.success("Report Saved")
elif page == "Knowledge Base":

    st.subheader("📚 Engineering Knowledge Base")

    pdf = st.file_uploader("Upload Engineering PDF", type=["pdf"])

    if pdf:

        files = {"file":pdf}

        requests.post(
            f"{API_URL}/upload_pdf",
            files=files
        )

        st.success("PDF Uploaded")
