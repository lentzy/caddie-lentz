# pages/6_Profile.py
import streamlit as st
from src.auth import require_auth, get_current_user_id, get_supabase_client, logout
from src.db import get_user_bag, set_user_bag
from src.constants import CLUB_LIST, ALL_CLUBS

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()
user = st.session_state.user

st.title("Profile & Settings")

# ── Display Name ──────────────────────────────
st.subheader("Account")
st.write(f"**Email:** {user.email}")

with st.form("display_name_form"):
    current_name = user.user_metadata.get("display_name", "") if user.user_metadata else ""
    new_name = st.text_input("Display name", value=current_name)
    if st.form_submit_button("Update Name"):
        client.auth.update_user({"data": {"display_name": new_name}})
        st.success("Name updated!")

# ── Change Password ───────────────────────────
st.subheader("Change Password")
with st.form("change_password_form"):
    new_password = st.text_input("New password", type="password")
    confirm_password = st.text_input("Confirm new password", type="password")
    if st.form_submit_button("Update Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match.")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            client.auth.update_user({"password": new_password})
            st.success("Password updated!")

st.divider()

# ── My Bag ────────────────────────────────────
st.subheader("My Bag")
st.write("Select the clubs you carry. These will appear first when tracking shots.")

current_bag = get_user_bag(client, user_id)

selected_clubs = []
for category, clubs in CLUB_LIST.items():
    st.write(f"**{category}**")
    cols = st.columns(len(clubs))
    for i, club in enumerate(clubs):
        if cols[i].checkbox(club, value=club in current_bag, key=f"bag_{club}"):
            selected_clubs.append(club)

if st.button("Save My Bag", type="primary"):
    set_user_bag(client, user_id, selected_clubs)
    st.success(f"Bag saved with {len(selected_clubs)} clubs.")
