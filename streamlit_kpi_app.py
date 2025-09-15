import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(layout="wide", page_title="KPI Dashboard")

st.title("📊 KPI Dashboard")

# --- Upload File ---
uploaded = st.file_uploader("Upload KPI Excel or CSV file", type=["xlsx", "xls", "csv"])
if uploaded is None:
    st.info("Please upload a KPI Excel or CSV file to start.")
    st.stop()

# --- Load File ---
try:
    df = pd.read_excel(uploaded)
except Exception:
    df = pd.read_csv(uploaded)

st.sidebar.header("⚙️ Settings")
date_col = st.sidebar.selectbox("Date column (for monthly grouping)", [None] + list(df.columns))
member_col = st.sidebar.selectbox("Member / Assignee column", [None] + list(df.columns))
task_col = st.sidebar.selectbox("Task ID/Name column", [None] + list(df.columns))

# --- Helper for auto-detect ---
def find_col(possible):
    for p in possible:
        for c in df.columns:
            if p.lower() in str(c).lower():
                return c
    return None

quality_col = find_col(["quality", "quality score", "qs", "qs%"])
revision_col = find_col(["revision", "revision rate", "rev rate"])
completed_col = find_col(["status", "completed", "task completed"])
ontime_col = find_col(["on-time", "on time", "ontime", "on time delivery"])
efficiency_col = find_col(["efficiency", "work efficiency"])
manhours_col = find_col(["actual work hours", "man-hour", "man hours", "hours"])

st.sidebar.subheader("Detected Columns")
st.sidebar.write({
    "Date": date_col,
    "Member": member_col,
    "Quality": quality_col,
    "Revision": revision_col,
    "Completed": completed_col,
    "On-time": ontime_col,
    "Efficiency": efficiency_col,
    "Man-hours": manhours_col
})

# --- Prepare Data ---
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["YearMonth"] = df[date_col].dt.to_period("M").astype(str)
else:
    df["YearMonth"] = "All"

# Convert percentages stored as "80%" → 0.8
def to_numeric_safe(ser
