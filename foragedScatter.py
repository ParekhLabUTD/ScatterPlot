import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
from oauth2client.service_account import ServiceAccountCredentials
import json
import subprocess
import datetime

# --- Page setup ---
st.set_page_config(page_title="Mouse Foraging Viewer", layout="wide")

# --- Initialize session state ---
if "selected_mice" not in st.session_state:
    st.session_state.selected_mice = []
if "plot_requested" not in st.session_state:
    st.session_state.plot_requested = False

# --- Get Git commit hash ---
def get_git_commit():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return commit
    except Exception:
        return "Unavailable"

# --- Load credentials ---
@st.cache_resource
def get_credentials():
    gcp_json = st.secrets["gcp_service_account"]
    creds_dict = json.loads(gcp_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# --- Load and preprocess data (cached) ---
@st.cache_data(ttl=600)  # Auto-refresh every 10 minutes
def load_data():
    load_data.timestamp = datetime.datetime.now()
    creds = get_credentials()
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1U6OTPPOpwrBcE9CHDjfGcAu3SuvdViijPTYwZ0Zg74c"
    worksheet = client.open_by_url(sheet_url).worksheet("Raw Data")

    data = worksheet.get_all_values()
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)

    df = df[['Mouse ID', 'Date', 'Total Foraged']].dropna()
    df['Mouse ID'] = df['Mouse ID'].astype(str)
    df['Date'] = df['Date'].astype(str).str.strip()
    df['Total Foraged'] = pd.to_numeric(df['Total Foraged'], errors='coerce')
    df = df.dropna(subset=['Total Foraged'])

    unique_dates = sorted(df['Date'].unique(), key=lambda d: pd.to_datetime(d, errors='coerce'))
    df['Date'] = pd.Categorical(df['Date'], categories=unique_dates, ordered=True)
    df = df.sort_values(['Mouse ID', 'Date'])

    return df

# --- Refresh + Metadata UI ---
col1, col2, col3 = st.columns([1.2, 5, 3])
with col1:
    if st.button("🔄 Refresh Data"):
        load_data.clear()
        st.session_state.plot_requested = False
        st.experimental_rerun()

with col3:
    last_updated = getattr(load_data, 'timestamp', None)
    if last_updated:
        st.markdown(f"**🕒 Last Updated:** `{last_updated.strftime('%Y-%m-%d %H:%M:%S')}`")
    else:
        st.markdown("**🕒 Last Updated:** `Unknown`")
    st.markdown(f"**🧬 Git Commit:** `{get_git_commit()}`")

# --- Load data ---
df = load_data()

# --- UI: Mouse selector and plot trigger ---
with st.form("mouse_selection_form"):
    st.title("🐭 Mouse Foraging Over Time")
    all_mice = sorted(df['Mouse ID'].unique())
    selected = st.multiselect("Select mice to display", all_mice, default=st.session_state.selected_mice)
    plot_btn = st.form_submit_button("📊 Plot Graph")

    if plot_btn:
        st.session_state.selected_mice = selected
        st.session_state.plot_requested = True

# --- Plotting ---
if st.session_state.plot_requested:
    selected_mice = st.session_state.selected_mice
    if selected_mice:
        fig, ax = plt.subplots(figsize=(10, 5))
        color_map = plt.cm.get_cmap('tab10', len(all_mice))

        for i, mouse in enumerate(all_mice):
            if mouse in selected_mice:
                sub_df = df[df['Mouse ID'] == mouse]
                ax.plot(sub_df['Date'], sub_df['Total Foraged'],
                        marker='o', linestyle='-', label=mouse, color=color_map(i))

        ax.set_title("Foraging by Mouse")
        ax.set_xlabel("Date")
        ax.set_ylabel("Total Foraged (g)")
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True)
        ax.legend(title="Mouse ID", bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)

        fig.tight_layout()
        st.pyplot(fig)
    else:
        st.warning("Please select at least one mouse to view data.")
