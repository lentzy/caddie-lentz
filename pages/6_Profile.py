# pages/6_Profile.py
import streamlit as st
from src.auth import require_auth, get_current_user_id, get_supabase_client, logout
from src.db import get_user_bag, set_user_bag, get_user_settings, upsert_user_settings
from src.constants import CLUB_LIST, ALL_CLUBS, HANDICAP_BENCHMARKS, HANDICAP_LABELS, BENCHMARK_SOURCE

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

st.divider()

# ── Stat Targets ───────────────────────────
st.subheader("Stat Targets")
st.caption(f"Targets used for Key Stats on the Dashboard. Benchmarks sourced from [{BENCHMARK_SOURCE}](https://{BENCHMARK_SOURCE}).")

settings = get_user_settings(client, user_id)
current_hdcp = settings.get("target_handicap", "20") if settings else "20"

hdcp_options = list(HANDICAP_LABELS.keys())  # ["0","5","10","15","20","25","custom"]
hdcp_labels = list(HANDICAP_LABELS.values())
current_idx = hdcp_options.index(current_hdcp) if current_hdcp in hdcp_options else 4  # default 20

selected_label = st.radio(
    "Select target level",
    options=hdcp_labels,
    index=current_idx,
    horizontal=True,
)
selected_hdcp = hdcp_options[hdcp_labels.index(selected_label)]

# Show reference table
st.markdown("**Benchmark values (FIR = Fairways in Regulation, GIR = Greens in Regulation):**")
import pandas as pd
bench_rows = [
    {
        "Handicap": HANDICAP_LABELS[k],
        "Putts / Round": f"{v['putts_per_round']:.1f}",
        "GIR %": f"{v['gir_pct']:.1%}",
        "FIR %": f"{v['fairways_hit_pct']:.1%}",
    }
    for k, v in HANDICAP_BENCHMARKS.items()
]
st.dataframe(pd.DataFrame(bench_rows), hide_index=True, use_container_width=True)

custom_putts, custom_gir, custom_fw = None, None, None
if selected_hdcp == "custom":
    st.markdown("**Set your custom targets:**")
    c1, c2, c3 = st.columns(3)
    default_putts = float(settings.get("custom_putts_per_round") or 34.0) if settings else 34.0
    default_gir   = float(settings.get("custom_gir_pct") or 0.30) if settings else 0.30
    default_fw    = float(settings.get("custom_fairways_hit_pct") or 0.45) if settings else 0.45
    custom_putts = c1.number_input("Putts / Round", min_value=25.0, max_value=45.0, value=default_putts, step=0.5)
    custom_gir   = c2.number_input("GIR %", min_value=0.05, max_value=0.80, value=default_gir, step=0.01, format="%.2f")
    custom_fw    = c3.number_input("FIR %", min_value=0.10, max_value=0.80, value=default_fw, step=0.01, format="%.2f")

if st.button("Save Targets", type="primary"):
    upsert_user_settings(client, user_id, selected_hdcp, custom_putts, custom_gir, custom_fw)
    st.success("Targets saved!")
