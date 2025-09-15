import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(layout="wide", page_title="KPI Dashboard")

st.title("KPI Dashboard - Upload Excel")

uploaded = st.file_uploader("Upload KPI Excel file", type=["xlsx","xls","csv"])
if uploaded is None:
    st.info("No file uploaded. Please upload your KPI Excel file to see results.")
    st.stop()
else:
    try:
        df = pd.read_excel(uploaded)
    except Exception:
        df = pd.read_csv(uploaded)

st.sidebar.header("Settings")
date_col = st.sidebar.selectbox("Date column (for monthly grouping)", options=[None]+list(df.columns), index=0)
member_col = st.sidebar.selectbox("Member / Assignee column", options=[None]+list(df.columns), index=0)
task_col = st.sidebar.selectbox("Task ID/Name column", options=[None]+list(df.columns), index=0)

# Auto-detect KPI columns
cols = list(df.columns)
def find_col(possible):
    for p in possible:
        for c in cols:
            if p.lower() in str(c).lower():
                return c
    return None

quality_col = find_col(["quality","quality score","qs","qs%"])
revision_col = find_col(["revision","revision rate","rev rate"])
completed_col = find_col(["status","completed","task completed"])
ontime_col = find_col(["on-time","on time","ontime","on time delivery"])
efficiency_col = find_col(["efficiency","work efficiency"])
manhours_col = find_col(["actual work hours","man-hour","man hours","hours"])

st.sidebar.write("Detected columns:")
st.sidebar.write(dict(date=date_col, member=member_col, quality=quality_col, revision=revision_col,
                      completed=completed_col, ontime=ontime_col, efficiency=efficiency_col, manhours=manhours_col))

# Convert date to YearMonth
if date_col:
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["YearMonth"] = df[date_col].dt.to_period("M").astype(str)
    except:
        df["YearMonth"] = df[date_col].astype(str)
else:
    df["YearMonth"] = "All"

# Ensure numeric
for c in [quality_col, revision_col, efficiency_col, manhours_col]:
    if c and c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# Completed tasks flag
if completed_col and completed_col in df.columns:
    df["_completed_flag"] = df[completed_col].apply(
        lambda x: 1 if str(x).strip().lower() in ["1","yes","done","completed","true"] 
        else (np.nan if pd.isna(x) else (1 if isinstance(x,(int,float)) and x>0 else 0))
    )
else:
    df["_completed_flag"] = 1

if ontime_col and ontime_col in df.columns:
    df[ontime_col] = pd.to_numeric(df[ontime_col], errors="coerce")

# Member + Month group
group_member_month = df.groupby([member_col,"YearMonth"]).agg(
    avg_quality = (quality_col, "mean") if quality_col else ("YearMonth", "count"),
    avg_revision = (revision_col, "mean") if revision_col else ("YearMonth", "count"),
    total_completed = ("_completed_flag", "sum"),
    avg_ontime = (ontime_col, "mean") if ontime_col else ("_completed_flag", "mean"),
    avg_efficiency = (efficiency_col, "mean") if efficiency_col else ("YearMonth", "count"),
    total_manhours = (manhours_col, "sum") if manhours_col else ("_completed_flag","sum")
).reset_index()

team_month = group_member_month.groupby("YearMonth").agg(
    avg_quality = ("avg_quality","mean"),
    avg_revision = ("avg_revision","mean"),
    total_completed = ("total_completed","sum"),
    avg_ontime = ("avg_ontime","mean"),
    avg_efficiency = ("avg_efficiency","mean"),
    total_manhours = ("total_manhours","sum")
).reset_index()

st.header("Member-level KPIs (monthly)")
st.dataframe(group_member_month)

st.header("Team-level KPIs (monthly)")
st.dataframe(team_month)

st.subheader("Monthly Team KPIs")
cols_to_chart = ["avg_quality","avg_revision","total_completed","avg_ontime","avg_efficiency","total_manhours"]
for c in cols_to_chart:
    if c in team_month.columns:
        fig = px.line(team_month, x="YearMonth", y=c, markers=True, title=c)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Per-task averages")
if task_col and task_col in df.columns:
    task_avg = df.groupby(task_col).agg(
        avg_quality = (quality_col, "mean") if quality_col else ("YearMonth","count"),
        avg_revision = (revision_col, "mean") if revision_col else ("YearMonth","count"),
        avg_ontime = (ontime_col, "mean") if ontime_col else ("YearMonth","count"),
        avg_efficiency = (efficiency_col, "mean") if efficiency_col else ("YearMonth","count"),
        manhours = (manhours_col, "sum") if manhours_col else ("YearMonth","count"),
        total_completed = ("_completed_flag","sum")
    ).reset_index()
    st.dataframe(task_avg)
    for c in ["avg_quality","avg_revision","avg_ontime","avg_efficiency","manhours"]:
        fig = px.bar(task_avg.sort_values(c,ascending=False).head(20), x=task_col, y=c, title=f"Per-task: {c}")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No task column selected.")

buf = BytesIO()
team_month.to_csv(buf, index=False)
buf.seek(0)
st.download_button("Download team-month CSV", data=buf, file_name="team_month.csv", mime="text/csv")
