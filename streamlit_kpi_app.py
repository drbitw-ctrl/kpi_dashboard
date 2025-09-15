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
def to_numeric_safe(series):
    if series is None:
        return None
    s = pd.to_numeric(series.astype(str).str.replace("%", "", regex=False), errors="coerce")
    return s.apply(lambda x: x / 100 if pd.notna(x) and x > 1 else x)

for c in [quality_col, revision_col, efficiency_col, ontime_col]:
    if c and c in df.columns:
        df[c] = to_numeric_safe(df[c])

if manhours_col and manhours_col in df.columns:
    df[manhours_col] = pd.to_numeric(df[manhours_col], errors="coerce")

# Completed flag
if completed_col and completed_col in df.columns:
    df["_completed_flag"] = df[completed_col].apply(
        lambda x: 1 if str(x).strip().lower() in ["1", "yes", "done", "completed", "true"]
        else (np.nan if pd.isna(x) else (1 if str(x).isdigit() and int(x) > 0 else 0))
    )
else:
    df["_completed_flag"] = 1

# --- Grouping ---
group_cols = ["YearMonth"]
if member_col:
    group_cols.insert(0, member_col)

group_member_month = df.groupby(group_cols).agg(
    avg_quality=(quality_col, "mean") if quality_col else ("YearMonth", "count"),
    avg_revision=(revision_col, "mean") if revision_col else ("YearMonth", "count"),
    total_completed=("_completed_flag", "sum"),
    avg_ontime=(ontime_col, "mean") if ontime_col else ("_completed_flag", "mean"),
    avg_efficiency=(efficiency_col, "mean") if efficiency_col else ("YearMonth", "count"),
    total_manhours=(manhours_col, "sum") if manhours_col else ("_completed_flag", "sum"),
).reset_index()

if member_col:
    team_month = group_member_month.groupby("YearMonth").agg(
        avg_quality=("avg_quality", "mean"),
        avg_revision=("avg_revision", "mean"),
        total_completed=("total_completed", "sum"),
        avg_ontime=("avg_ontime", "mean"),
        avg_efficiency=("avg_efficiency", "mean"),
        total_manhours=("total_manhours", "sum")
    ).reset_index()
else:
    team_month = group_member_month.copy()

# --- Display ---
st.header("👤 Member-level KPIs (monthly)" if member_col else "📈 Team KPIs")
st.dataframe(group_member_month)

st.header("👥 Team-level KPIs (monthly)")
st.dataframe(team_month)

# --- Charts ---
st.subheader("📅 Monthly Team KPI Trends")
cols_to_chart = ["avg_quality", "avg_revision", "total_completed", "avg_ontime", "avg_efficiency", "total_manhours"]

for c in cols_to_chart:
    if c in team_month.columns and team_month[c].notna().sum() > 0:
        fig = px.line(team_month, x="YearMonth", y=c, markers=True, title=c)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No data for {c}")

# --- Per-task averages ---
if task_col and task_col in df.columns:
    st.subheader("📌 Per-task averages")
    task_avg = df.groupby(task_col).agg(
        avg_quality=(quality_col, "mean") if quality_col else ("YearMonth", "count"),
        avg_revision=(revision_col, "mean") if revision_col else ("YearMonth", "count"),
        avg_ontime=(ontime_col, "mean") if ontime_col else ("YearMonth", "count"),
        avg_efficiency=(efficiency_col, "mean") if efficiency_col else ("YearMonth", "count"),
        manhours=(manhours_col, "sum") if manhours_col else ("YearMonth", "count"),
        total_completed=("_completed_flag", "sum"),
    ).reset_index()
    st.dataframe(task_avg)

    for c in ["avg_quality", "avg_revision", "avg_ontime", "avg_efficiency", "manhours"]:
        if c in task_avg.columns and task_avg[c].notna().sum() > 0:
            fig = px.bar(
                task_avg.sort_values(c, ascending=False).head(20),
                x=task_col, y=c, title=f"Top 20 Tasks - {c}"
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No task column selected. Select one from the sidebar to see per-task graphs.")

# --- Download CSV ---
buf = BytesIO()
team_month.to_csv(buf, index=False)
buf.seek(0)
st.download_button(
    "💾 Download team-month CSV",
    data=buf,
    file_name="team_month.csv",
    mime="text/csv"
)
