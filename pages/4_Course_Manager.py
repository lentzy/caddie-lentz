# pages/4_Course_Manager.py
import streamlit as st
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_courses, get_tees, create_course, create_tee, update_course, delete_course, delete_tee

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

st.title("Course Manager")

# ── Browse Courses ────────────────────────────
search = st.text_input("Search courses", placeholder="Filter by name...")
courses = get_courses(client, search=search if search else None)

if not courses:
    st.info("No courses found. Add one below.")
else:
    for course in courses:
        with st.expander(f"**{course['name']}** — {course['city']}, {course['state']}"):
            st.write(f"Added by: {course['created_by_user_id'][:8]}...")
            st.write(f"Par: {course['par_per_hole']}")

            tees = get_tees(client, course["id"])
            if tees:
                st.write("**Tees:**")
                for tee in tees:
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"- {tee['tee_name']} | Rating: {tee['rating']} | Slope: {tee['slope']}")
                    if tee["created_by_user_id"] == user_id:
                        if col2.button("Delete", key=f"del_tee_{tee['id']}"):
                            delete_tee(client, tee["id"])
                            st.rerun()
            else:
                st.write("No tees added yet.")

            # Add tee form
            with st.form(f"add_tee_{course['id']}"):
                st.write("**Add a tee:**")
                tee_name = st.text_input("Tee name")
                c1, c2 = st.columns(2)
                rating = c1.number_input("Rating", 60.0, 80.0, 72.0, 0.1)
                slope = c2.number_input("Slope", 55, 155, 113)
                st.write("Yardage per hole:")
                yard_cols = st.columns(9)
                yardages = [yard_cols[i % 9].number_input(f"H{i+1}", 50, 700, 400, key=f"yd_{course['id']}_{i}") for i in range(18)]
                if st.form_submit_button("Add Tee") and tee_name:
                    create_tee(client, user_id, course["id"], tee_name, rating, slope, yardages)
                    st.success("Tee added!")
                    st.rerun()

            if course["created_by_user_id"] == user_id:
                from src.db import get_rounds
                referencing_rounds = client.table("rounds").select("id").eq("course_id", course["id"]).limit(1).execute()
                if referencing_rounds.data:
                    st.caption("This course has rounds logged against it and cannot be deleted.")
                else:
                    if st.button("Delete Course", key=f"del_course_{course['id']}", type="secondary"):
                        delete_course(client, course["id"])
                        st.rerun()

st.divider()

# ── Add New Course ────────────────────────────
st.subheader("Add a New Course")
with st.form("new_course_form"):
    name = st.text_input("Course name")
    c1, c2 = st.columns(2)
    city = c1.text_input("City")
    state = c2.text_input("State")
    st.write("Par per hole:")
    par_cols = st.columns(9)
    pars = [par_cols[i % 9].number_input(f"H{i+1}", 3, 6, 4, key=f"par_new_{i}") for i in range(18)]
    if st.form_submit_button("Add Course"):
        if name and city and state:
            create_course(client, user_id, name, city, state, pars)
            st.success(f"'{name}' added!")
            st.rerun()
        else:
            st.error("Please fill in name, city, and state.")
