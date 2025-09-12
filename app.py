import os
import tempfile
import streamlit as st
import pandas as pd
from risk_assessment.extract_pdf import extract_clauses
from risk_assessment.analyze_clauses import analyze_all_batches
import gspread
from google.oauth2.service_account import Credentials
import altair as alt
import base64
from PIL import Image

# ---------------- Custom Styling ----------------
def add_custom_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

        .stApp {
            font-family: 'Poppins', sans-serif;
            animation: gradientBG 15s ease infinite;
            transition: background 0.5s ease-in-out;
        }

        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }

        h1 {
            font-family: 'Poppins', sans-serif;
            transition: transform 0.3s ease, text-shadow 0.3s ease;
        }
        h1:hover {
            transform: scale(1.05);
            text-shadow: 0 0 8px rgba(0, 128, 255, 0.7);
        }

        h2, h3 {
            font-family: 'Poppins', sans-serif;
        }

        p, .stText, .stMarkdown {
            font-family: 'Poppins', sans-serif;
            transition: color 0.3s ease;
        }

        .stContainer {
            background-color: rgba(255, 255, 255, 0.85);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .stContainer:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 40px rgba(0, 0, 0, 0.2);
        }

        .stButton>button:hover {
            background-color: #4CAF50;
            color: white;
            transform: scale(1.05);
            transition: background-color 0.3s ease, color 0.3s ease, transform 0.2s ease;
        }

        .stFileUploader>div:hover {
            border: 2px dashed #4CAF50;
            transition: border 0.3s ease;
        }

        .stFileUploader>div:focus-within {
            border: 2px dashed #2196F3;
            transition: border 0.3s ease;
        }

        .stProgress>div>div>div>div {
            transition: width 0.5s ease;
        }

        .glow {
            box-shadow: 0 0 15px rgba(0, 128, 255, 0.5);
            transition: box-shadow 0.3s ease;
        }

        .scroll-smooth {
            scroll-behavior: smooth;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

add_custom_style()

# ---------------- Background Image ----------------
def add_background_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded_string}"), 
                              linear-gradient(-45deg, #1e3c72, #2a5298, #1e3c72, #2a5298);
            background-size: 400% 400%, cover;
            background-position: center;
            background-repeat: no-repeat;
            animation: gradientBG 15s ease infinite;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

image_path = "images/bgimg.png"
add_background_image(image_path)

# ---------------- Page Config ----------------
st.set_page_config(page_title="AI Compliance Checker", layout="wide", page_icon="📑")

# ---------------- Header ----------------
header_img_path = "images/headimg.png"
with open(header_img_path, "rb") as image_file:
    encoded_header = base64.b64encode(image_file.read()).decode()

st.markdown(
    f"""
    <div style="text-align: center;" class="scroll-smooth">
        <h1 class="glow" style="font-size: 2.5em; font-weight: bold;">📑 AI Powered Regulatory Compliance Checker</h1>
        <img src="data:image/png;base64,{encoded_header}" width="600" style="margin-top: 20px;"/>
        <p style="font-size: 1.2em; margin-top: 10px;">Upload a contract PDF and get clause-level risk insights with actionable recommendations.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------- Google Sheets Setup ----------------
GOOGLE_AUTH_FILE = "services.json"
GSHEET_ID = "your_gsheet_id"
SHEET_NAME = "Sheet1"

creds = Credentials.from_service_account_file(
    GOOGLE_AUTH_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gs_client = gspread.authorize(creds)
worksheet = gs_client.open_by_key(GSHEET_ID).worksheet(SHEET_NAME)

# ---------------- File Upload ----------------
uploaded_file = st.file_uploader("📝 Upload your contract (PDF)", type=["pdf"])
batch_size = 5

# ---------------- Session State ----------------
if "clauses" not in st.session_state:
    st.session_state.clauses = None
if "results" not in st.session_state:
    st.session_state.results = None
if "df" not in st.session_state:
    st.session_state.df = None

if uploaded_file:
    # Clause Extraction
    if st.session_state.clauses is None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        st.info("📂 Extracting clauses...")
        st.session_state.clauses = extract_clauses(tmp_path)
        st.info(f"🔍 Found {len(st.session_state.clauses)} clauses.")

    # Clause Analysis
    if st.session_state.results is None:
        with st.spinner("Analyzing clauses... Please wait."):
            st.info("⏳ Analyzing clauses in batches...")
            progress_bar = st.progress(0)
            results = []

            for i in range(0, len(st.session_state.clauses), batch_size):
                batch = st.session_state.clauses[i:i + batch_size]
                batch_results = analyze_all_batches(batch, start_id=i + 1, batch_size=batch_size)
                results.extend(batch_results)
                progress_bar.progress(min((i + batch_size) / len(st.session_state.clauses), 1.0))

            progress_bar.empty()
            st.success("✅ Analysis completed!")
            st.session_state.results = results

    # DataFrame Creation
    if st.session_state.df is None:
        df = pd.DataFrame(st.session_state.results)
        df["Risk Level"] = df.get("Risk Level", "Unknown")
        df["Risk Score"] = df.get("Risk Score", "0%").fillna("0%")
        st.session_state.df = df
    else:
        df = st.session_state.df

    # ---------------- Metrics ----------------
    high = df[df["Risk Level"] == "High"].shape[0]
    medium = df[df["Risk Level"] == "Medium"].shape[0]
    low = df[df["Risk Level"] == "Low"].shape[0]

    if not df.empty:
        # FIXED: Safe conversion of Risk Score
        numeric_scores = (
            df["Risk Score"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        numeric_scores = pd.to_numeric(numeric_scores, errors="coerce").fillna(0)
        top_clause_idx = numeric_scores.idxmax()
        top_clause = df.loc[top_clause_idx]
    else:
        top_clause = None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Total Clauses", len(df))
    col2.metric("⚠️ High Risk", high)
    col3.metric("🟡 Medium Risk", medium)
    col4.metric("✅ Low Risk", low)

    if top_clause is not None:
        st.markdown("### 🚨 Highest Risk Clause")
        st.write(f"**Clause ID {top_clause['Clause ID']}** — {top_clause['Clause Feedback & Fix']}")

    # ---------------- Risk Level Chart ----------------
    st.markdown("### 📊 Risk Level Distribution")
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
        .properties(width=400, height=300)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    # ---------------- Clause Data ----------------
    st.markdown("### 📋 Clause Analysis")
    sheet_data = worksheet.get_all_records()
    sheet_df = pd.DataFrame(sheet_data)
    st.dataframe(sheet_df, use_container_width=True)

    # ---------------- Download CSV ----------------
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Clause Analysis CSV",
        data=csv,
        file_name="clause_analysis.csv",
        mime="text/csv"
    )

    # ---------------- Google Sheets Button ----------------
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/edit#gid=0"
    st.markdown(
        f"""
        <div style="text-align: left; margin-top: 5px;">
            <a href="{gsheet_url}" target="_blank">
                <button style="
                    background-color:#4285F4;
                    color:white;
                    border:none;
                    padding:10px 18px;
                    border-radius:5px;
                    cursor:pointer;
                    font-size:16px;">
                    📊 View Full Report in Google Sheets
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    st.info("👆 Upload a contract PDF to begin.")

