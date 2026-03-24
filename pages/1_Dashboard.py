# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_rounds, get_hole_scores_for_rounds, get_in_progress_round, get_courses_by_ids, get_user_settings
from src.analytics import compute_user_metrics, build_focus_area_cards, METRIC_DISPLAY_NAMES, get_targets, LOWER_IS_BETTER
from src.constants import BENCHMARKS, HOLES_FOR_ROUND, BENCHMARK_SOURCE

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
user_settings = get_user_settings(client, user_id)
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
                d_color = "inverse" if area["metric"] in LOWER_IS_BETTER else "normal"
                if area["metric"].endswith("_pct"):
                    st.metric(label="Your average", value=f"{val:.1%}", delta=f"{val - target:.1%} vs target", delta_color=d_color)
                else:
                    st.metric(label="Your average", value=f"{val:.1f}", delta=f"{val - target:+.1f} vs target", delta_color=d_color)
                if area.get("insight"):
                    st.caption(area["insight"])

st.divider()

# ── Scoring Trend ─────────────────────────────
targets, target_label = get_targets(user_settings)
st.subheader("Scoring Trend")
from src.constants import HANDICAP_BENCHMARKS as _HB
_hdcp = (user_settings or {}).get("target_handicap", "20")
_target_score = _HB.get(_hdcp, _HB["20"])["avg_score"]

trend_df = rounds_df.sort_values("date").reset_index(drop=True)
trend_df["round_number"] = range(1, len(trend_df) + 1)
trend_df["vs_target"] = trend_df["total_score"] - _target_score
trend_df["round_label"] = trend_df["name"].where(trend_df["name"].notna(), trend_df["date"])

fig = px.line(
    trend_df,
    x="round_number",
    y="vs_target",
    markers=True,
    custom_data=["round_label", "total_score"],
    labels={"vs_target": "Score vs Target", "round_number": "Round"},
    title=f"Score vs Target ({target_label}, target avg {_target_score:.0f})",
)
fig.update_traces(
    line_color="#2ecc71",
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        f"Score: %{{customdata[1]}} (target {_target_score:.0f})<br>"
        "vs Target: %{y:+.2f}<extra></extra>"
    ),
)
fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
fig.update_xaxes(dtick=1)
st.plotly_chart(fig, use_container_width=True)

recent_two = rounds_df.sort_values("date", ascending=False).head(2)
r_cols = st.columns(2)
for col, (_, row) in zip(r_cols, recent_two.iterrows()):
    course_name = (row.get("courses") or {}).get("name", "Unknown")
    label = row.get("name") or row["date"]
    score = row.get("total_score")
    vs_str = f" ({score - _target_score:+.0f} vs target)" if score is not None else ""
    with col:
        with st.container(border=True):
            st.markdown(f"**{label}** — {course_name}")
            st.markdown(f"Score: **{score}**{vs_str}")
st.page_link("pages/3_Round_History.py", label="View all rounds →")

# ── Key Stats ─────────────────────────────────
st.subheader("Key Stats")

# Per-round data for sparklines
rounds_sorted = rounds_df.sort_values("date").reset_index(drop=True)
rounds_sorted["round_num"] = range(1, len(rounds_sorted) + 1)
per_round = hole_scores_df.groupby("round_id").agg(
    putts=("putts", "sum"),
    gir=("green_in_regulation", "mean"),
).reset_index()
fw_per_round = (
    hole_scores_df[hole_scores_df["fairway_hit"].notna()]
    .groupby("round_id")["fairway_hit"].mean()
    .rename("fw_pct").reset_index()
)
trend_df = rounds_sorted.merge(per_round, left_on="id", right_on="round_id", how="left")
trend_df = trend_df.merge(fw_per_round, left_on="id", right_on="round_id", how="left")

def _sparkline(df, y, color, target, target_fmt):
    fig = px.line(df, x="round_num", y=y, markers=True)
    fig.update_traces(line_color=color, marker=dict(size=5))
    fig.add_hline(y=target, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(
        height=120, margin=dict(l=42, r=10, t=4, b=24),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title="",
                   showline=True, linecolor="gray", linewidth=1),
        yaxis=dict(showgrid=False, zeroline=False, title="",
                   showline=True, linecolor="gray", linewidth=1,
                   tickvals=[target], ticktext=[target_fmt],
                   tickfont=dict(size=10, color="gray")),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

stat_cols = st.columns(3)
with stat_cols[0]:
    putts = hole_scores_df.groupby("round_id")["putts"].sum().mean()
    t = targets["putts_per_round"]
    st.metric("Avg Putts / Round", f"{putts:.1f}", delta=f"{putts - t:+.1f} vs target of {t:.0f} ({target_label})", delta_color="inverse")
    st.plotly_chart(_sparkline(trend_df, "putts", "#3498db", t, f"{t:.0f}"), use_container_width=True)
with stat_cols[1]:
    gir = hole_scores_df["green_in_regulation"].mean()
    t = targets["gir_pct"]
    st.metric("GIR %", f"{gir:.1%}", delta=f"{gir - t:+.1%} vs target of {t:.0%} ({target_label})", delta_color="normal")
    st.plotly_chart(_sparkline(trend_df, "gir", "#2ecc71", t, f"{t:.0%}"), use_container_width=True)
with stat_cols[2]:
    fw = hole_scores_df[hole_scores_df["fairway_hit"].notna()]
    fw_pct = fw["fairway_hit"].mean() if not fw.empty else 0
    t = targets["fairways_hit_pct"]
    st.metric("Fairways Hit %", f"{fw_pct:.1%}", delta=f"{fw_pct - t:+.1%} vs target of {t:.0%} ({target_label})", delta_color="normal")
    st.plotly_chart(_sparkline(trend_df, "fw_pct", "#e67e22", t, f"{t:.0%}"), use_container_width=True)

st.caption(f"Targets based on [{BENCHMARK_SOURCE}](https://{BENCHMARK_SOURCE}). Change your target level in Profile.")
