# pages/2_New_Round.py
import streamlit as st
from datetime import date
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import (
    get_courses, get_tees, create_round, get_round,
    get_hole_scores, upsert_hole_score, complete_round, create_course, create_tee
)
from src.constants import HOLES_PLAYED_OPTIONS, HOLES_FOR_ROUND

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

# Initialize session state for round flow
if "round_step" not in st.session_state:
    st.session_state.round_step = "setup"  # setup | playing | complete
if "active_round_id" not in st.session_state:
    st.session_state.active_round_id = None
if "current_hole_idx" not in st.session_state:
    st.session_state.current_hole_idx = 0

st.title("New Round")

# ── STEP: SETUP ───────────────────────────────
if st.session_state.round_step == "setup":
    st.subheader("Round Setup")

    search = st.text_input("Search courses", placeholder="Type a course name...")
    courses = get_courses(client, search=search if search else None)

    selected_course_id = None
    tee_id = None

    ADD_NEW = "+ Add new course..."
    course_options = {f"{c['name']} — {c['city']}, {c['state']}": c["id"] for c in courses}
    selectbox_options = list(course_options.keys()) + [ADD_NEW]
    selected_label = st.selectbox("Select course", options=selectbox_options)

    if selected_label == ADD_NEW:
        with st.form("add_course_form"):
            new_name = st.text_input("Course name")
            col1, col2 = st.columns(2)
            new_city = col1.text_input("City")
            new_state = col2.text_input("State")
            new_website = st.text_input("Website (optional)", placeholder="https://...")
            st.write("Par for each hole (1–18):")
            par_cols = st.columns(9)
            pars = []
            for i in range(18):
                pars.append(par_cols[i % 9].number_input(f"H{i+1}", min_value=3, max_value=6, value=4, key=f"par_{i}"))
            if st.form_submit_button("Add Course", type="primary"):
                if new_name and new_city and new_state:
                    create_course(client, user_id, new_name, new_city, new_state, pars, website=new_website or None)
                    st.success(f"Course '{new_name}' added!")
                    st.rerun()
                else:
                    st.error("Please fill in name, city, and state.")
    else:
        selected_course_id = course_options.get(selected_label)

    # Tee selection
    if selected_course_id:
        tees = get_tees(client, course_id=selected_course_id)
        ADD_NEW_TEE = "+ Add new tee..."
        tee_options = {f"{t['tee_name']} (Rating: {t['rating']}, Slope: {t['slope']})": t["id"] for t in tees}
        tee_selectbox_options = list(tee_options.keys()) + [ADD_NEW_TEE]
        selected_tee_label = st.selectbox("Select tee", options=tee_selectbox_options)

        if selected_tee_label == ADD_NEW_TEE:
            with st.form("add_tee_form"):
                tee_name = st.text_input("Tee name (e.g. Blue, White)")
                col1, col2 = st.columns(2)
                rating = col1.number_input("Course rating", min_value=60.0, max_value=80.0, value=72.0, step=0.1)
                slope = col2.number_input("Slope", min_value=55, max_value=155, value=113)
                st.write("Yardage for each hole (1–18):")
                yard_cols = st.columns(9)
                yardages = []
                for i in range(18):
                    yardages.append(yard_cols[i % 9].number_input(f"H{i+1}", min_value=50, max_value=700, value=400, key=f"yd_{i}"))
                if st.form_submit_button("Add Tee", type="primary") and tee_name:
                    create_tee(client, user_id, selected_course_id, tee_name, rating, slope, yardages)
                    st.success(f"Tee '{tee_name}' added!")
                    st.rerun()
        else:
            tee_id = tee_options.get(selected_tee_label)

    holes_label = st.selectbox("Holes played", options=list(HOLES_PLAYED_OPTIONS.keys()))
    round_date = st.date_input("Date", value=date.today())
    round_name = st.text_input("Round name (optional)", placeholder="Leave blank to auto-generate")
    notes = st.text_area("Notes (optional)", height=68)

    if st.button("Start Round", type="primary", disabled=(not selected_course_id or not tee_id)):
        new_round = create_round(
            client, user_id,
            course_id=selected_course_id,
            tee_id=tee_id,
            date=str(round_date),
            holes_played=HOLES_PLAYED_OPTIONS[holes_label],
            notes=notes or None,
            name=round_name or None,
        )
        st.session_state.active_round_id = new_round["id"]
        st.session_state.round_step = "playing"
        st.session_state.current_hole_idx = 0
        st.rerun()

# ── STEP: PLAYING ─────────────────────────────
elif st.session_state.round_step == "playing":
    round_id = st.session_state.active_round_id
    round_data = get_round(client, round_id)

    if round_data is None:
        st.error("Round not found. Please start a new round.")
        st.session_state.round_step = "setup"
        st.rerun()

    holes = HOLES_FOR_ROUND[round_data["holes_played"]]
    total_holes = len(holes)
    hole_idx = st.session_state.current_hole_idx
    hole_number = holes[hole_idx]

    from src.db import get_course, get_tee
    course = get_course(client, round_data["course_id"])
    tee = get_tee(client, round_data["tee_id"])
    par = course["par_per_hole"][hole_number - 1]
    yardage = tee["yardage_per_hole"][hole_number - 1]

    st.progress((hole_idx) / total_holes, text=f"Hole {hole_idx + 1} of {total_holes}")
    st.subheader(f"Hole {hole_number} — Par {par} — {yardage} yards")

    existing_scores = get_hole_scores(client, round_id)
    existing = next((h for h in existing_scores if h["hole_number"] == hole_number), None)

    with st.form(f"hole_{hole_number}_form"):
        col1, col2, col3 = st.columns(3)

        score = col1.number_input(
            "Score", min_value=1, max_value=15,
            value=existing["score"] if existing else par,
        )
        if score > 10:
            st.warning("Score > 10 — are you sure?")

        putts = col2.number_input(
            "Putts", min_value=0, max_value=6,
            value=existing["putts"] if existing else 2,
        )

        penalties = col3.number_input(
            "Penalties", min_value=0, max_value=10,
            value=existing["penalties"] if existing else 0,
        )

        col4, col5 = st.columns(2)
        if par == 3:
            fairway_hit = None
        else:
            default_fairway = existing["fairway_hit"] if existing else False
            fairway_hit = col4.checkbox("Fairway hit", value=bool(default_fairway) if default_fairway is not None else False)

        gir = col5.checkbox(
            "Green in regulation",
            value=existing["green_in_regulation"] if existing else False,
        )

        if putts > score:
            st.error("Putts cannot exceed score.")

        col_prev, col_next = st.columns(2)
        prev_clicked = col_prev.form_submit_button("← Previous", disabled=(hole_idx == 0))
        next_label = "Finish Round →" if hole_idx == total_holes - 1 else "Next Hole →"
        next_clicked = col_next.form_submit_button(next_label, type="primary")

        if next_clicked or prev_clicked:
            if putts > score:
                st.error("Cannot save: putts exceed score.")
                st.stop()

            upsert_hole_score(
                client, round_id, hole_number,
                score=int(score), putts=int(putts),
                fairway_hit=fairway_hit,
                green_in_regulation=gir,
                penalties=int(penalties),
            )

            if next_clicked:
                if hole_idx == total_holes - 1:
                    complete_round(client, round_id)
                    st.session_state.round_step = "complete"
                else:
                    st.session_state.current_hole_idx += 1
            elif prev_clicked:
                st.session_state.current_hole_idx -= 1

            st.rerun()

    # Shot tracking — only available once the hole score has been saved
    from src.db import get_shots, create_shot, delete_shots_for_hole, get_user_bag
    from src.constants import (
        ALL_CLUBS, SHOT_TYPE_OPTIONS, LIE_OPTIONS,
        CONTACT_OPTIONS, OUTCOME_OPTIONS, PENALTY_REASON_OPTIONS,
        MISS_DISTANCE_OPTIONS
    )

    if not existing:
        st.caption("Save this hole score (click Next Hole →) to enable shot tracking.")
    else:
        existing_shots = get_shots(client, existing["id"])
        shot_label = f"Track Shots ({len(existing_shots)} logged)" if existing_shots else "Track Shots (optional)"
        with st.expander(shot_label):
            user_bag = get_user_bag(client, user_id)
            if not user_bag:
                st.info("No bag set up — showing all clubs. [Set up your bag in Profile →](Profile)")
            club_options = user_bag if user_bag else ALL_CLUBS

            with st.form(f"shot_form_{hole_number}"):
                s_col1, s_col2, s_col3 = st.columns(3)
                shot_club = s_col1.selectbox("Club", options=club_options)
                shot_type = s_col2.selectbox("Shot type (lie location)", options=SHOT_TYPE_OPTIONS)
                lie = s_col3.selectbox("Lie quality", options=LIE_OPTIONS)

                s_col4, s_col5, s_col6 = st.columns(3)
                distance_to_hole = s_col4.number_input("Distance to hole (yds)", min_value=0, max_value=600, value=150)
                distance_hit = s_col5.number_input("Distance hit (yds, optional)", min_value=0, max_value=400, value=0)
                outcome = s_col6.selectbox("Outcome", options=OUTCOME_OPTIONS)

                contact = st.multiselect("Contact (select all that apply)", options=CONTACT_OPTIONS, default=["good"])
                md_col1, md_col2 = st.columns(2)
                miss_direction = md_col1.selectbox("Miss direction (if applicable)", options=["none", "left", "right"])
                miss_distance = md_col2.selectbox("Miss distance (if applicable)", options=["none"] + MISS_DISTANCE_OPTIONS)
                penalty_reason = None
                if outcome == "penalty":
                    penalty_reason = st.selectbox("Penalty reason", options=PENALTY_REASON_OPTIONS)

                if st.form_submit_button("Add Shot", type="primary"):
                    create_shot(
                        client,
                        hole_score_id=existing["id"],
                        shot_number=len(existing_shots) + 1,
                        distance_to_hole=distance_to_hole if distance_to_hole > 0 else None,
                        club=shot_club,
                        shot_type=shot_type,
                        lie=lie,
                        contact=contact,
                        miss_direction=miss_direction if miss_direction != "none" else None,
                        miss_distance=miss_distance if miss_distance != "none" else None,
                        outcome=outcome,
                        penalty_reason=penalty_reason,
                        distance_hit=distance_hit if distance_hit > 0 else None,
                    )
                    st.rerun()

    st.divider()
    col_save, col_abandon = st.columns(2)

    if col_save.button("Save & Exit", use_container_width=True):
        st.session_state.round_step = "setup"
        st.session_state.active_round_id = None
        st.session_state.current_hole_idx = 0
        st.switch_page("pages/1_Dashboard.py")

    if not st.session_state.get("confirm_abandon"):
        if col_abandon.button("Abandon Round", use_container_width=True, type="secondary"):
            st.session_state.confirm_abandon = True
            st.rerun()
    else:
        st.warning("This will delete the round and all saved hole scores. Are you sure?")
        c1, c2 = st.columns(2)
        if c1.button("Yes, delete it", type="primary", use_container_width=True):
            from src.db import delete_round
            delete_round(client, st.session_state.active_round_id)
            st.session_state.round_step = "setup"
            st.session_state.active_round_id = None
            st.session_state.current_hole_idx = 0
            st.session_state.confirm_abandon = False
            st.switch_page("pages/1_Dashboard.py")
        if c2.button("Cancel", use_container_width=True):
            st.session_state.confirm_abandon = False
            st.rerun()

# ── STEP: COMPLETE ────────────────────────────
elif st.session_state.round_step == "complete":
    round_id = st.session_state.active_round_id
    round_data = get_round(client, round_id)
    st.success(f"Round complete! Total score: **{round_data['total_score']}**")
    if round_data.get("differential") is not None:
        st.write(f"Differential: {round_data['differential']:.1f}")

    col1, col2 = st.columns(2)
    if col1.button("View Round Summary"):
        st.session_state.selected_round_id = round_id
        st.switch_page("pages/3_Round_History.py")
    if col2.button("Back to Dashboard"):
        st.session_state.round_step = "setup"
        st.session_state.active_round_id = None
        st.session_state.current_hole_idx = 0
        st.switch_page("pages/1_Dashboard.py")
