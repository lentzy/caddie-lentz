# pages/3_Round_History.py
import streamlit as st
import pandas as pd
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import (
    get_rounds, get_round, get_hole_scores, get_shots,
    upsert_hole_score, complete_round, get_course, get_tee
)

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

st.title("Round History")

rounds = get_rounds(client, user_id, status="complete", limit=50)

if not rounds:
    st.info("No completed rounds yet.")
    st.stop()

# ── Round List ────────────────────────────────
rounds_df = pd.DataFrame(rounds)
rounds_df["course_name"] = rounds_df["courses"].apply(lambda x: x["name"] if x else "Unknown")
rounds_df["tee_name"] = rounds_df["tees"].apply(lambda x: x["tee_name"] if x else "Unknown")

display_df = rounds_df[["date", "course_name", "tee_name", "holes_played", "total_score"]].copy()
display_df.columns = ["Date", "Course", "Tee", "Holes", "Score"]
display_df = display_df.sort_values("Date", ascending=False)

selected_idx = st.dataframe(
    display_df,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
)

if not selected_idx["selection"]["rows"]:
    st.info("Select a round above to view details.")
    st.stop()

selected_row = display_df.iloc[selected_idx["selection"]["rows"][0]]
selected_round_id = rounds_df.iloc[selected_idx["selection"]["rows"][0]]["id"]

st.divider()
st.subheader(f"{selected_row['Course']} — {selected_row['Date']}")
st.write(f"**Score:** {selected_row['Score']} | **Tee:** {selected_row['Tee']} | **Holes:** {selected_row['Holes']}")

# ── Hole-by-Hole Breakdown ────────────────────
hole_scores = get_hole_scores(client, selected_round_id)
if hole_scores:
    hs_df = pd.DataFrame(hole_scores)[["hole_number", "score", "putts", "fairway_hit", "green_in_regulation", "penalties"]]
    hs_df.columns = ["Hole", "Score", "Putts", "Fairway", "GIR", "Penalties"]
    st.dataframe(hs_df, use_container_width=True, hide_index=True)

# ── Edit Round ────────────────────────────────
with st.expander("Edit this round"):
    st.write("Select a hole to edit:")
    hole_options = {f"Hole {h['hole_number']}": h for h in hole_scores}
    selected_hole_label = st.selectbox("Hole", options=list(hole_options.keys()))
    h = hole_options[selected_hole_label]

    round_data = get_round(client, selected_round_id)
    course = get_course(client, round_data["course_id"])
    par = course["par_per_hole"][h["hole_number"] - 1]

    with st.form("edit_hole_form"):
        col1, col2, col3 = st.columns(3)
        score = col1.number_input("Score", 1, 15, value=h["score"])
        putts = col2.number_input("Putts", 0, 6, value=h["putts"])
        penalties = col3.number_input("Penalties", 0, 10, value=h["penalties"])

        col4, col5 = st.columns(2)
        fw_options = ["yes", "no", "na"]
        fairway_hit = col4.selectbox("Fairway hit", fw_options, index=fw_options.index(h["fairway_hit"]))
        gir = col5.checkbox("Green in regulation", value=h["green_in_regulation"])

        save = st.form_submit_button("Save Changes")
        if save:
            if putts > score:
                st.error("Putts cannot exceed score.")
            else:
                upsert_hole_score(client, selected_round_id, h["hole_number"],
                                  score=score, putts=putts, fairway_hit=fairway_hit,
                                  green_in_regulation=gir, penalties=penalties)
                # Recompute totals
                complete_round(client, selected_round_id)
                st.success("Hole updated!")
                st.rerun()
