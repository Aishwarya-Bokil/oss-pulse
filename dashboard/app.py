import streamlit as st
from google.cloud import bigquery

PROJECT = "oss-pulse-509119"
TABLE = f"{PROJECT}.oss_pulse_analytics.repo_growth_daily"
client = bigquery.Client(project=PROJECT)

@st.cache_data(ttl=600)
def load_data():
    return client.query(f"SELECT * FROM `{TABLE}` ORDER BY snapshot_date").to_dataframe()

st.set_page_config(page_title="OSS Pulse", layout="wide")
st.title("OSS Pulse")

df = load_data()
repos = sorted(df["repo_name"].unique())
selected = st.multiselect("Repos", repos, default=repos)
filtered = df[df["repo_name"].isin(selected)]
filtered["snapshot_date"] = filtered["snapshot_date"].astype(str)


st.subheader("Star trajectory")
st.line_chart(filtered.pivot(index="snapshot_date", columns="repo_name", values="stars"))

st.subheader("Fork trajectory")
st.line_chart(filtered.pivot(index="snapshot_date", columns="repo_name", values="forks"))

st.subheader("Open-issue backlog trend")
st.line_chart(filtered.pivot(index="snapshot_date", columns="repo_name", values="open_issues"))

st.subheader("Fastest growing (latest day, by star % change)")
latest = df["snapshot_date"].max()
leaderboard = (df[df["snapshot_date"] == latest]
    .sort_values("stars_pct_change", ascending=False)
    [["repo_name", "stars_pct_change", "stars_change"]])
st.dataframe(leaderboard, use_container_width=True)