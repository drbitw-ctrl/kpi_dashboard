import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(layout="wide", page_title="KPI Dashboard")

st.title("📊 KPI Dashboard")
st.markdown("Upload your KPI data and get **monthly, per-member, and per-task performance analytics** with charts.")

# --- Upload File ---
uploaded = st.file_uploader("📂 Upload KPI Excel or CSV file", type=["xlsx", "xls", "csv"])
if uploaded is None:
    st.info("Please upload a file to start.")
    st.stop()

# --- Load File ---
try:
    df = pd.read_excel(uploaded)
except Exception:
    df = pd.read_csv(uploaded)

st.sidebar.header("⚙️ Settings")
st.sidebar.write("Choose which columns represent key metrics so the dashboard can calculate correctly.")

date_col = st.sidebar.selectbox("📅 Date column (for monthly grouping)", [None] + list(df.columns))
member_col = st.sidebar.selectbox("👤 Member / Assignee column", [None] + list(df.columns))
task_col = st.sidebar.selectbox("📝 Task ID/Name column", [None] + list(df.columns))

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

st.sidebar.subheader("🔎 Auto-Detected Columns")
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
    df["YearMonth"] = df[date_col].dt.strftime("%Y-%m")
else:
    df["YearMonth"] = "All"

# Convert quality score to percentage (if numeric and <=5)
if quality_col and quality_col in df.columns:
    df[quality_col] = pd.to_numeric(df[quality_col], errors="coerce")
    if df[quality_col].max() <= 5:
        df[quality_col] = (df[quality_col] / 5) * 100

# Convert other numeric fields
def to_numeric_safe(series):
    if series is None:
        return None
    s = pd.to_numeric(series.astype(str).str.replace("%", "", regex=False), errors="coerce")
    return s.apply(lambda x: x / 100 if pd.notna(x) and x > 1 and x <= 100 else x)

for c in [revision_col, efficiency_col, ontime_col]:
    if c and c in df.columns:
        df[c] = to_numeric_safe(df[c]) * 100  # convert to percentage

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

# --- Display Data ---
st.header("👤 Member-level KPIs (monthly)" if member_col else "📈 Team KPIs")
st.dataframe(group_member_month.style.format({
    "avg_quality": "{:.2f}%",
    "avg_revision": "{:.2f}%",
    "avg_ontime": "{:.2f}%",
    "avg_efficiency": "{:.2f}%",
    "total_manhours": "{:.2f}"
}))

# --- Per-task averages ---
if task_col and task_col in df.columns:
    st.subheader("📝 Per-task averages")
    task_avg = df.groupby(task_col).agg(
        avg_quality=(quality_col, "mean") if quality_col else ("YearMonth", "count"),
        avg_revision=(revision_col, "mean") if revision_col else ("YearMonth", "count"),
        avg_ontime=(ontime_col, "mean") if ontime_col else ("YearMonth", "count"),
        avg_efficiency=(efficiency_col, "mean") if efficiency_col else ("YearMonth", "count"),
        manhours=(manhours_col, "sum") if manhours_col else ("YearMonth", "count"),
        total_completed=("_completed_flag", "sum"),
    ).reset_index()
    st.dataframe(task_avg.style.format({
        "avg_quality": "{:.2f}%",
        "avg_revision": "{:.2f}%",
        "avg_ontime": "{:.2f}%",
        "avg_efficiency": "{:.2f}%",
        "manhours": "{:.2f}"
    }))

    for c in ["avg_quality", "avg_revision", "avg_ontime", "avg_efficiency", "manhours"]:
        if c in task_avg.columns and task_avg[c].notna().sum() > 0:
            fig = px.bar(task_avg.sort_values(c, ascending=False).head(20),
                         x=task_col, y=c, title=f"Top 20 Tasks - {c.replace('_',' ').title()}")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("ℹ️ Select a task column in the sidebar to see per-task charts.")

# --- Download CSV ---
buf = BytesIO()
team_month.to_csv(buf, index=False)
buf.seek(0)
st.download_button("💾 Download team-month CSV", data=buf,
                   file_name="team_month.csv", mime="text/csv")
