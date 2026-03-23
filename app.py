# app.py
import streamlit as st
from src.auth import is_authenticated, login, register, logout, get_supabase_client, send_password_reset

st.set_page_config(
    page_title="Caddie Lentz",
    page_icon="⛳",
    layout="wide",
)

# Initialize Supabase client on first load
get_supabase_client()


def login_page():
    st.title("⛳ Caddie Lentz")
    st.caption("Golf score and statistics tracker")

    tab_login, tab_register, tab_reset = st.tabs(["Log In", "Register", "Forgot Password"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
            if submitted:
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    success, error = login(email, password)
                    if success:
                        st.rerun()
                    else:
                        st.error(f"Login failed: {error}")

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            password2 = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                elif password != password2:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success, error = register(email, password)
                    if success:
                        st.success("Account created! Check your email to confirm, then log in.")
                    else:
                        st.error(f"Registration failed: {error}")

    with tab_reset:
        with st.form("reset_form"):
            email = st.text_input("Email address")
            submitted = st.form_submit_button("Send Reset Link", use_container_width=True)
            if submitted:
                if not email:
                    st.error("Please enter your email address.")
                else:
                    success, message = send_password_reset(email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


if is_authenticated():
    with st.sidebar:
        user = st.session_state.user
        st.write(f"Logged in as **{user.email}**")
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

    pg = st.navigation([
        st.Page("pages/1_Dashboard.py", title="Dashboard"),
        st.Page("pages/2_New_Round.py", title="New Round"),
        st.Page("pages/3_Round_History.py", title="Round History"),
        st.Page("pages/4_Course_Manager.py", title="Course Manager"),
        st.Page("pages/5_Stats.py", title="Stats"),
        st.Page("pages/6_Profile.py", title="Profile"),
    ])
else:
    pg = st.navigation([st.Page(login_page, title="Login")])

pg.run()
