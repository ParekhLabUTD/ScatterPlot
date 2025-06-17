import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
from oauth2client.service_account import ServiceAccountCredentials
import json

# ---- Google Sheets API setup ----
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
gcp_json = st.secrets["gcp_service_account"]
creds_dict = json.loads(gcp_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet_url = "https://docs.google.com/spreadsheets/d/1U6OTPPOpwrBcE9CHDjfGcAu3SuvdViijPTYwZ0Zg74c"
spreadsheet = client.open_by_url(sheet_url)
worksheet = spreadsheet.worksheet("Raw Data")

# --- Load Data ---
data = worksheet.get_all_values()
headers = data[0]
rows = data[1:]
df = pd.DataFrame(rows, columns=headers)

# --- Preprocessing ---
df = df[['Mouse ID', 'Date', 'Total Foraged']].dropna()
df['Mouse ID'] = df['Mouse ID'].astype(str)
df['Date'] = df['Date'].astype(str).str.strip()
df['Total Foraged'] = pd.to_numeric(df['Total Foraged'], errors='coerce')
df = df.dropna(subset=['Total Foraged'])
unique_dates = sorted(df['Date'].unique(), key=lambda d: pd.to_datetime(d, errors='coerce'))
df['Date'] = pd.Categorical(df['Date'], categories=unique_dates, ordered=True)
df = df.sort_values(['Mouse ID', 'Date'])

# --- Streamlit UI ---
st.title("Mouse Foraging Over Time")
all_mice = sorted(df['Mouse ID'].unique())

selected_mice = st.multiselect("Select mice to display", all_mice, default=all_mice)

if selected_mice:
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.get_cmap('tab10', len(all_mice))

    for i, mouse in enumerate(all_mice):
        if mouse in selected_mice:
            sub_df = df[df['Mouse ID'] == mouse]
            ax.plot(sub_df['Date'], sub_df['Total Foraged'], marker='o', linestyle='-', label=mouse, color=colors(i))

    ax.set_title("Foraging by Mouse")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Foraged (g)")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True)

# 🔄 Move legend outside plot
    ax.legend(title="Mouse ID", bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)

    fig.tight_layout()  # Helps with spacing

    st.pyplot(fig)

else:
    st.warning("Please select at least one mouse.")
