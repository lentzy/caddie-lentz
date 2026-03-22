# pages/1_Dashboard.py
import streamlit as st
from src.auth import require_auth
require_auth()
st.title("Dashboard")
st.info("Coming soon.")
