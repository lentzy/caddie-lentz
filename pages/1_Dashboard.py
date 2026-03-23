# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_rounds, get_hole_scores_for_rounds, get_in_progress_round, get_courses_by_ids
from src.analytics import compute_user_metrics, build_focus_area_cards, METRIC_DISPLAY_NAMES
from src.constants import BENCHMARKS, HOLES_FOR_ROUND

require_auth()

st.title("Dashboard")

client = get_supabase_client()
user_id = get_current_user_id()

# ── In-Progress Round Banner ──────────────────
in_progress = get_in_progress_round(client, user_id)
if in_progress:
    course_name = in_progress.get("courses", {}).get("name", "Unknown Course")
    round_label = in_progress.get("name") or in_progress["date"]
    st.warning(f"Round in progress: **{round_label}** — {course_name}")
    if st.button("Continue Round"):
        holes = HOLES_FOR_ROUND[in_progress["holes_played"]]
        saved = {h["hole_number"] for h in get_hole_scores(client, in_progress["id"])}
        next_idx = next((i for i, h in enumerate(holes) if h not in saved), len(holes) - 1)
        st.session_state["active_round_id"] = in_progress["id"]
        st.session_state["round_step"] = "playing"
        st.session_state["current_hole_idx"] = next_idx
        st.switch_page("pages/2_New_Round.py")

# ── Load data ──────────────────────────────────
rounds = get_rounds(client, user_id, status="complete", limit=20)
rounds_df = pd.DataFrame(rounds) if rounds else pd.DataFrame()

if rounds_df.empty:
    st.info("No rounds logged yet. Start a new round to see your stats here.")
    if st.button("Start New Round"):
        st.switch_page("pages/2_New_Round.py")
    st.stop()

# Load all hole scores for these rounds in a single query
round_ids = rounds_df["id"].tolist()
hole_scores_df = pd.DataFrame(get_hole_scores_for_rounds(client, round_ids)) if round_ids else pd.DataFrame()

# Join par from course data so analytics can compute scoring_avg_par3/4/5
if not hole_scores_df.empty:
    courses_map = {c["id"]: c for c in get_courses_by_ids(client, rounds_df["course_id"].unique().tolist())}
    round_course = dict(zip(rounds_df["id"], rounds_df["course_id"]))
    hole_scores_df["par"] = hole_scores_df.apply(
        lambda r: courses_map[round_course[r["round_id"]]]["par_per_hole"][r["hole_number"] - 1], axis=1
    )

user_metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
n_shot_rounds = 0  # Shot data integration: count rounds with shots (Task 13 enhancement)

# Compute recent vs. prior metrics for trend weighting (requires >= 6 rounds)
recent_metrics, prior_metrics = {}, {}
if len(rounds_df) >= 6:
    rounds_sorted = rounds_df.sort_values("date", ascending=False).reset_index(drop=True)
    recent_ids = set(rounds_sorted.head(5)["id"])
    prior_ids = set(rounds_sorted.iloc[5:10]["id"])
    recent_hs = hole_scores_df[hole_scores_df["round_id"].isin(recent_ids)]
    prior_hs = hole_scores_df[hole_scores_df["round_id"].isin(prior_ids)]
    recent_rounds = rounds_sorted[rounds_sorted["id"].isin(recent_ids)]
    prior_rounds = rounds_sorted[rounds_sorted["id"].isin(prior_ids)]
    recent_metrics = compute_user_metrics(recent_rounds, recent_hs, pd.DataFrame())
    prior_metrics = compute_user_metrics(prior_rounds, prior_hs, pd.DataFrame())

# ── Focus Areas Card ──────────────────────────
st.subheader("Focus Areas")
focus_areas = build_focus_area_cards(
    user_metrics, pd.DataFrame(), hole_scores_df, n_shot_rounds,
    recent_metrics=recent_metrics, prior_metrics=prior_metrics,
)

if not focus_areas:
    st.info("Not enough data yet to identify focus areas. Log a few more rounds.")
else:
    cols = st.columns(len(focus_areas))
    for col, area in zip(cols, focus_areas):
        with col:
            with st.container(border=True):
                st.markdown(f"### {area['display_name']}")
                val = area["user_value"]
                target = area["target_value"]
                if area["metric"].endswith("_pct"):
                    st.metric(label="Your average", value=f"{val:.1%}", delta=f"{val - target:.1%} vs target", delta_color="inverse")
                else:
                    st.metric(label="Your average", value=f"{val:.1f}", delta=f"{val - target:+.1f} vs target", delta_color="inverse")
                if area.get("insight"):
                    st.caption(area["insight"])

st.divider()

# ── Scoring Trend ─────────────────────────────
st.subheader("Scoring Trend")
fig = px.line(
    rounds_df.sort_values("date"),
    x="date",
    y="total_score",
    markers=True,
    labels={"total_score": "Score", "date": "Date"},
    title="Score per Round (last 20)",
)
fig.update_traces(line_color="#2ecc71")
st.plotly_chart(fig, use_container_width=True)

# ── Key Stat Trends ───────────────────────────
st.subheader("Key Stats")
stat_cols = st.columns(3)
with stat_cols[0]:
    putts = hole_scores_df.groupby("round_id")["putts"].sum().mean()
    st.metric("Avg Putts / Round", f"{putts:.1f}", help="Lower is better. Bogey avg: 36")
with stat_cols[1]:
    gir = hole_scores_df["green_in_regulation"].mean()
    st.metric("GIR %", f"{gir:.1%}", help="Higher is better. Bogey avg: 25%")
with stat_cols[2]:
    fw = hole_scores_df[hole_scores_df["fairway_hit"].notna()]
    fw_pct = fw["fairway_hit"].mean() if not fw.empty else 0
    st.metric("Fairways Hit %", f"{fw_pct:.1%}", help="Higher is better. Bogey avg: 40%")
