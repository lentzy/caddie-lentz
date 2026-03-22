# pages/5_Stats.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_rounds, get_hole_scores, get_shots, get_hole_score
from src.analytics import compute_user_metrics, interpolate_benchmark
from src.constants import BENCHMARKS

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

st.title("Stats & Analysis")

rounds = get_rounds(client, user_id, status="complete", limit=20)
if not rounds:
    st.info("Log some rounds to see stats.")
    st.stop()

rounds_df = pd.DataFrame(rounds)
all_hole_scores = []
for r in rounds:
    all_hole_scores.extend(get_hole_scores(client, r["id"]))
hole_scores_df = pd.DataFrame(all_hole_scores)

user_metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
avg_score = user_metrics.get("avg_score", 90)
target = interpolate_benchmark(avg_score)

# ── Benchmark Comparison Table ────────────────
st.subheader("Where You Stand")
metric_rows = []
for metric, target_val in target.items():
    user_val = user_metrics.get(metric)
    if user_val is None:
        continue
    scratch_val = BENCHMARKS["scratch"][metric]
    bogey_val = BENCHMARKS["bogey"][metric]
    metric_rows.append({
        "Metric": metric.replace("_", " ").title(),
        "You (last 20)": round(user_val, 2),
        "Your Target": round(target_val, 2),
        "Bogey": round(bogey_val, 2),
        "Scratch": round(scratch_val, 2),
    })
st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Score Distribution ────────────────────────
st.subheader("Score Distribution")
fig = px.histogram(rounds_df, x="total_score", nbins=15,
                   labels={"total_score": "Score"},
                   title="Distribution of Scores")
st.plotly_chart(fig, use_container_width=True)

# ── Stat Trends Over Time ─────────────────────
st.subheader("Stat Trends Over Time")
putts_by_round = hole_scores_df.groupby("round_id")["putts"].sum().reset_index()
putts_by_round = putts_by_round.merge(rounds_df[["id", "date"]], left_on="round_id", right_on="id")

fig2 = px.line(putts_by_round.sort_values("date"), x="date", y="putts",
               markers=True, title="Putts per Round",
               labels={"putts": "Total Putts", "date": "Date"})
st.plotly_chart(fig2, use_container_width=True)

# ── Shot Analysis ─────────────────────────────
st.subheader("Shot Analysis")

all_shots = []
hs_ids = hole_scores_df["id"].tolist() if "id" in hole_scores_df.columns else []
for hs_id in hs_ids[:200]:  # cap to avoid slow loads
    all_shots.extend(get_shots(client, hs_id))

if not all_shots:
    st.info("No shot data tracked yet. Enable shot tracking during a round to see analysis here.")
else:
    shots_df = pd.DataFrame(all_shots)
    outcome_counts = shots_df.groupby(["club", "outcome"]).size().reset_index(name="count")
    fig3 = px.bar(outcome_counts, x="club", y="count", color="outcome",
                  title="Shot Outcomes by Club",
                  labels={"count": "Shots", "club": "Club"})
    st.plotly_chart(fig3, use_container_width=True)
