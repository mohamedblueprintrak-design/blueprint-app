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

# ---------------- CSS ---------------- #

st.markdown("""
<style>

.stApp{
background-color:#f1f5f9;
background-image:
linear-gradient(rgba(14,165,233,0.05) 1px,transparent 1px),
linear-gradient(90deg,rgba(14,165,233,0.05) 1px,transparent 1px);
background-size:40px 40px;
}

.bp-card{
background:white;
padding:25px;
border-radius:18px;
border:1px solid #e2e8f0;
box-shadow:0 8px 25px rgba(0,0,0,0.06);
transition:0.3s;
text-align:center;
}

.bp-card:hover{
transform:translateY(-6px);
box-shadow:0 25px 50px rgba(0,0,0,0.1);
}

.metric-number{
font-size:32px;
font-weight:700;
}

.metric-label{
color:#64748b;
font-size:14px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ---------------- #

st.markdown("""
<div style="
background: linear-gradient(135deg,#0ea5e9,#1e40af);
padding:35px;
border-radius:20px;
color:white;
margin-bottom:25px;
">

<h1>📐 BluePrint Engineering Consultancy</h1>
<p>AI Powered Engineering Operating System</p>

</div>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ---------------- #

st.sidebar.title("📂 Navigation")

page = st.sidebar.radio(
    "",
    [
        "Dashboard",
        "AI Assistant",
        "BOQ Analyzer",
        "Defects",
        "Site Reports",
        "Knowledge Base"
    ]
)

# ---------------- METRIC CARD ---------------- #

def metric_card(icon,value,label,color):

    st.markdown(f"""
    <div class="bp-card">

    <div style="font-size:30px">{icon}</div>

    <div class="metric-number" style="color:{color}">
    {value}
    </div>

    <div class="metric-label">
    {label}
    </div>

    </div>
    """, unsafe_allow_html=True)

# ---------------- DASHBOARD ---------------- #

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
        metric_card("💰",data.get("cost",0),"Project Cost","#16a34a")

    with col3:
        metric_card("⚠️",len(data.get("defects",[])),"Defects","#ef4444")

    with col4:
        metric_card("📁",len(data.get("files",[])),"Files","#7c3aed")

# ---------------- AI ASSISTANT ---------------- #

elif page == "AI Assistant":

    st.subheader("🤖 Blue AI Engineering Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask Blue about engineering...")

    if prompt:

        st.session_state.messages.append(
            {"role":"user","content":prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"question":prompt}
            ).json()

            answer = response.get("answer","No response")

        except:
            answer = "Server not responding"

        with st.chat_message("assistant"):
            st.markdown(answer)

        st.session_state.messages.append(
            {"role":"assistant","content":answer}
        )

# ---------------- BOQ ANALYZER ---------------- #

elif page == "BOQ Analyzer":

    st.subheader("💰 Bill of Quantities Analyzer")

    file = st.file_uploader(
        "Upload BOQ Excel",
        type=["xlsx","xls"]
    )

    if file:

        df = pd.read_excel(file)

        st.dataframe(df)

        if "Total" in df.columns:

            total = df["Total"].sum()

            st.success(f"Total Cost: {total}")

# ---------------- DEFECTS ---------------- #

elif page == "Defects":

    st.subheader("⚠️ Site Defects Manager")

    defect = st.text_input("Defect Description")

    if st.button("Add Defect"):

        try:

            requests.post(
                f"{API_URL}/defect",
                json={"text":defect}
            )

            st.success("Defect Added")

        except:
            st.error("Server Error")

# ---------------- REPORTS ---------------- #

elif page == "Site Reports":

    st.subheader("📝 Daily Site Reports")

    report = st.text_area("Write Site Report")

    if st.button("Save Report"):

        try:

            requests.post(
                f"{API_URL}/report",
                json={"text":report}
            )

            st.success("Report Saved")

        except:
            st.error("Server Error")

# ---------------- KNOWLEDGE BASE ---------------- #

elif page == "Knowledge Base":

    st.subheader("📚 Engineering Knowledge Base")

    pdf = st.file_uploader(
        "Upload Engineering PDF",
        type=["pdf"]
    )

    if pdf:

        files = {"file":pdf}

        try:

            requests.post(
                f"{API_URL}/upload_pdf",
                files=files
            )

            st.success("PDF Uploaded Successfully")

        except:
            st.error("Upload Failed")
