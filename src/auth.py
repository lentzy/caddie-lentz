# src/auth.py
import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Initialize or return the Supabase client from session state."""
    if "supabase" not in st.session_state:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase


def refresh_session_if_needed():
    """Refresh the auth token if expired. Clears user from session if no valid session."""
    client = get_supabase_client()
    try:
        session = client.auth.get_session()
        if session is None:
            st.session_state.pop("user", None)
    except Exception:
        st.session_state.pop("user", None)


def is_authenticated() -> bool:
    return "user" in st.session_state and st.session_state.user is not None


def require_auth():
    """Call at top of every page. Stops rendering if not authenticated."""
    refresh_session_if_needed()
    if not is_authenticated():
        st.warning("Please log in to continue.")
        st.stop()


def login(email: str, password: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        return True, ""
    except Exception as e:
        return False, str(e)


def register(email: str, password: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    client = get_supabase_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        if response.user:
            st.session_state.user = response.user
            return True, ""
        return False, "Registration failed. Check your email to confirm your account, then log in."
    except Exception as e:
        return False, str(e)


def logout():
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)


def get_current_user():
    return st.session_state.get("user")


def get_current_user_id() -> str | None:
    user = get_current_user()
    return str(user.id) if user else None


def send_password_reset(email: str) -> tuple[bool, str]:
    """Send a password reset email. Returns (success, message)."""
    client = get_supabase_client()
    try:
        client.auth.reset_password_for_email(email)
        return True, "Password reset email sent. Check your inbox."
    except Exception as e:
        return False, str(e)
