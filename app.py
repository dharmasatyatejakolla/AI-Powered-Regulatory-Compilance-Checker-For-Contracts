import os
import tempfile
import base64
import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import altair as alt

from risk_assessment.extract_pdf import extract_clauses
from risk_assessment.analyze_clauses import analyze_all_batches
from config import ModelManager

# ------------------- Styling -------------------
def add_custom_style():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    .stApp {
        font-family: 'Poppins', sans-serif;
        transition: background 0.5s ease-in-out;
        font-size: 18px;
    }
    
    h1 {
        font-size: 2.5em !important;
        font-weight: 700 !important;
        transition: transform 0.3s ease, text-shadow 0.3s ease;
    }
    h1:hover {
        transform: scale(1.05);
        text-shadow: 0 0 10px rgba(0, 128, 255, 0.8);
    }

    h2, h3 {
        font-size: 1.6em !important;
    }

    .stContainer {
        background-color: rgba(255,255,255,0.9);
        border-radius: 14px;
        padding: 25px;
        box-shadow: 0 6px 35px rgba(0,0,0,0.1);
    }

    .stButton>button {
        font-size: 1.1em !important;
        padding: 12px 22px !important;
        border-radius: 8px !important;
    }
    .stButton>button:hover {
        background-color: #4CAF50;
        color: white;
        transform: scale(1.07);
    }

    .stFileUploader>div {
        font-size: 1.1em !important;
        padding: 18px !important;
    }
    .stFileUploader>div:hover {
        border: 2px dashed #4CAF50;
    }

    .stDataFrame, .dataframe {
        font-size: 1.05em !important;
    }

    .metric-container {
        font-size: 1.2em !important;
    }

    .glow { 
        box-shadow: 0 0 18px rgba(0, 128, 255, 0.5);
    }

    .bottom-right {
        text-align: right;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# Background image
def add_background_image():
    image_path = "images/bgimg.png"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{encoded}"), 
                          linear-gradient(-45deg, #1e3c72, #2a5298);
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
    </style>
    """, unsafe_allow_html=True)

add_custom_style()
add_background_image()
st.set_page_config(page_title="AI Compliance Checker", layout="wide", page_icon="📑")

# ------------------- Google Sheets -------------------
GOOGLE_AUTH_FILE = "services.json"
GSHEET_ID = "1NfuT_zRcjG93a6pFg7RrHv424N4yQympge5siowY_tw"
SHEET_NAME = "Sheet1"
creds = Credentials.from_service_account_file(GOOGLE_AUTH_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gs_client = gspread.authorize(creds)
worksheet = gs_client.open_by_key(GSHEET_ID).worksheet(SHEET_NAME)

# ------------------- Session State -------------------
if "page" not in st.session_state:
    st.session_state.page = "upload"
if "clauses" not in st.session_state:
    st.session_state.clauses = None
if "results" not in st.session_state:
    st.session_state.results = None
if "df" not in st.session_state:
    st.session_state.df = None

# ------------------- Header (Upload Page Only) -------------------
def show_header():
    st.markdown("""
    <div style="text-align: center; padding: 20px; background-color: rgba(255,255,255,0.9); 
                border-radius: 12px; margin-bottom: 25px; box-shadow: 0px 6px 18px rgba(0,0,0,0.15);">
        <h1 style="color:#1e3c72;">📑 AI Powered Regulatory Compliance Checker</h1>
        <p style="font-size:1.25em; color:#333;">
            Upload a contract in PDF format to automatically extract clauses, 
            assess regulatory risks, and receive AI-powered compliance recommendations for improvement.
        </p>
    </div>
    """, unsafe_allow_html=True)

    image_path = "images/headimg.png"
    if os.path.exists(image_path):
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:20px;">
                <img src="data:image/png;base64,{base64.b64encode(open(image_path, "rb").read()).decode()}" 
                     style="width:650px; max-width:95%; border-radius:12px;" />
            </div>
            """,
            unsafe_allow_html=True
        )

# ------------------- Upload Page -------------------
def upload_page():
    show_header()
    uploaded_file = st.file_uploader("📝 Upload your contract (PDF)", type=["pdf"])
    batch_size = 5

    if uploaded_file:
        if st.session_state.clauses is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            st.info("📂 Extracting clauses...")
            st.session_state.clauses = extract_clauses(tmp_path)
            st.info(f"🔍 Found {len(st.session_state.clauses)} clauses.")

        if st.session_state.results is None:
            with st.spinner("Analyzing clauses..."):
                progress = st.progress(0)
                results = []
                for i in range(0, len(st.session_state.clauses), batch_size):
                    batch = st.session_state.clauses[i:i + batch_size]
                    batch_results = analyze_all_batches(batch, start_id=i+1, batch_size=batch_size)
                    results.extend(batch_results)
                    progress.progress(min((i + batch_size) / len(st.session_state.clauses), 1.0))
                progress.empty()
                st.success("✅ Analysis completed!")
                st.session_state.results = results

        if st.session_state.df is None:
            df = pd.DataFrame(st.session_state.results)
            df["Risk Score"] = df.get("Risk Score", "0%").fillna("0%")
            st.session_state.df = df

        try:
            rows = [st.session_state.df.columns.tolist()] + st.session_state.df.astype(str).values.tolist()
            worksheet.clear()
            worksheet.update("A1", rows)

            # Full screen loader
            st.markdown("""
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                        background-color: white; display: flex; justify-content: center; 
                        align-items: center; z-index: 9999; font-size: 2.2em; color: #1e3c72;">
                ⏳ Loading Results...
            </div>
            """, unsafe_allow_html=True)

            st.session_state.page = "results"
            st.rerun()
        except Exception as e:
            st.error(f"⚠ Upload failed: {e}")

# ------------------- Results Page -------------------
def results_page():
    df = st.session_state.df
    if df is None or df.empty:
        st.error("No data available.")
        return

    # ---------------- Page Header ----------------
    st.markdown("""
    <div style="text-align: center; padding: 20px; background-color: rgba(255,255,255,0.9); 
                border-radius: 12px; margin-bottom: 25px; box-shadow: 0px 6px 18px rgba(0,0,0,0.15);">
        <h1 style="color:#1e3c72;">📊 Compliance Risk Analysis Results</h1>
        <p style="font-size:1.2em; color:#333;">
            Your contract has been analyzed clause-by-clause. The sections below summarize compliance risks, 
            provide a distribution overview, and highlight AI-generated recommendations for improvements.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- Metrics ----------------
    st.markdown("###      Key Metrics:")
    st.info("These metrics summarize the overall compliance profile of your contract, "
            "helping you quickly assess areas that require the most attention.")

    high = df[df["Risk Level"] == "High"].shape[0]
    medium = df[df["Risk Level"] == "Medium"].shape[0]
    low = df[df["Risk Level"] == "Low"].shape[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Total Clauses", len(df))
    col2.metric("🔴 High Risk", high)
    col3.metric("🟡 Medium Risk", medium)
    col4.metric("🟢 Low Risk", low)

    # ---------------- Highest Risk Clause ----------------
    st.markdown("### 🔎 Highest Risk Clause:")
    high_risk_df = df[df["Risk Level"] == "High"]

    if not high_risk_df.empty:
        high_risk_df["Risk Score (%)"] = high_risk_df["Risk Score"].str.replace("%", "").astype(float)
        top_clause = high_risk_df.sort_values(by="Risk Score (%)", ascending=False).iloc[0]

        st.markdown(f"""
        <div style="padding: 15px; background-color: rgba(255,0,0,0.08); border-left: 6px solid red; 
                    border-radius: 8px; margin-top: 15px;">
            <b>Clause ID:</b> {top_clause['Clause ID']} <br>
            <b>Risk Score:</b> {top_clause['Risk Score']} <br>
            <b>Clause:</b> {top_clause['Contract Clause']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ No high-risk clauses detected in this contract.")

    # ---------------- Chart ----------------
    st.markdown("### 📊 Risk Level Distribution:")
    st.caption("The chart below shows how identified clauses are distributed across High, Medium, "
               "and Low risk levels, giving you a quick snapshot of compliance health.")

    risk_counts = df["Risk Level"].value_counts().reindex(["High", "Medium", "Low"], fill_value=0).reset_index()
    risk_counts.columns = ["Risk Level", "Count"]

    color_scale = alt.Scale(domain=["High", "Medium", "Low"], range=["red", "yellow", "green"])
    chart = (
        alt.Chart(risk_counts)
        .mark_bar()
        .encode(
            x=alt.X("Risk Level:N", sort=["High", "Medium", "Low"]),
            y="Count:Q",
            color=alt.Color("Risk Level:N", scale=color_scale),
            tooltip=["Risk Level", "Count"]
        )
        .properties(width=450, height=350)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    # ---------------- Clause Analysis ----------------
    st.markdown("### 📋 Clause Analysis:")

    desc_col, filter_col = st.columns([7, 2])
    with desc_col:
        st.caption(
            "This table provides a breakdown of each extracted clause with its assessed risk level. "
            "Use the filter on the right to focus on a specific risk category."
        )
    with filter_col:
        filter_option = st.selectbox(
            "Filter Risk Level",
            options=["All", "High", "Medium", "Low"],
            index=0,
            label_visibility="collapsed"
        )

    if filter_option != "All":
        filtered_df = df[df["Risk Level"] == filter_option]
    else:
        filtered_df = df

    st.dataframe(filtered_df, use_container_width=True, height=500)

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        " Download Filtered Clause Analysis CSV ",
        data=csv,
        file_name="clause_analysis.csv",
        mime="text/csv"
    )

    # ---------------- AI-Rewritten Clauses ----------------
    st.markdown("### ⚡ AI-Rewritten Clauses")
    st.caption("This section shows AI-rewritten clauses (only for High risk).")

    if "show_rewrites" not in st.session_state:
        st.session_state.show_rewrites = False

    if not st.session_state.show_rewrites:
        if st.button("✍️ Show AI-Rewritten Clauses"):
            st.session_state.show_rewrites = True
            st.rerun()

    if st.session_state.show_rewrites:
        sugg_df = df[df["Risk Level"] == "High"].copy()

        if "AI-Rewritten Clause" not in sugg_df.columns:
            sugg_df["AI-Rewritten Clause"] = "⚠️ No rewritten version available"
        if "Clause Feedback & Fix" not in sugg_df.columns:
            sugg_df["Clause Feedback & Fix"] = "No feedback available"

        keep_cols = [
            "Clause ID",
            "Contract Clause",
            "Risk Level",
            "Clause Feedback & Fix",
            "AI-Modified Clause"
        ]
        sugg_df = sugg_df[[c for c in keep_cols if c in sugg_df.columns]]

        if sugg_df.empty:
            st.info("✅ No high-risk clauses to rewrite.")
        else:
            st.dataframe(sugg_df, use_container_width=True, height=400)

            sugg_csv = sugg_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                " Download AI-Rewritten Clauses CSV ",
                data=sugg_csv,
                file_name="ai_rewritten_clauses.csv",
                mime="text/csv"
            )

    # ---------------- Google Sheets Button ----------------
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/edit#gid=0"
    st.markdown(f"""
    <div style="text-align: left; margin-top: 15px;">
        <a href="{gsheet_url}" target="_blank">
            <button style="font-size:1.1em; background-color:#4285F4; color:white; padding:12px 22px; 
                           border-radius:6px; cursor:pointer;">
                📊 View Full Report in Google Sheets
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- Back Button ----------------
    st.markdown("""
    <div class="bottom-right">
        <form action="" method="get">
            <button type="submit" style="font-size:1.1em; background-color:#1e3c72; color:white; 
                   padding:12px 22px; border-radius:6px; cursor:pointer;"
                onclick="window.location.reload();">⬅ Go Back to Upload</button>
        </form>
    </div>
    """, unsafe_allow_html=True)


# ------------------- Router -------------------
if st.session_state.page == "upload":
    upload_page()
elif st.session_state.page == "results":
    results_page()
