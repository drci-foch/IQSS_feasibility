import pandas as pd
import streamlit as st
from datetime import datetime
from app_conf import EASILY_API_URL, LIFEN_API_URL
from style import custom_css

# Import modular components
from sidebar import render_sidebar
from data_processor import process_data
from tabs_handler import render_initial_tabs, display_tabs_content

st.set_page_config(
    page_title="Outil de Requête Lettre de liaison Patients",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(custom_css, unsafe_allow_html=True)

def main():
    # En-tête
    st.markdown(
        "<h1 class='main-header'>Outil de Requête Lettre de liaison Patients</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Un outil pour analyser les Lettre de liaison patients validés et leur diffusion via Lifen."
    )

    # Initialize session state
    if "easily_data" not in st.session_state:
        st.session_state.easily_data = None
    if "lifen_data" not in st.session_state:
        st.session_state.lifen_data = None

    # Render sidebar and get user selections
    with st.sidebar:
        start_date, end_date, filter_specialite, filter_result, filter_channel, run_query = render_sidebar()

    # Process data if requested or display cached data
    if run_query:
        df_easily, df_lifen = process_data(start_date, end_date, filter_specialite, filter_result, filter_channel)
        if df_easily is not None:
            display_tabs_content(df_easily, df_lifen)
    elif st.session_state.easily_data:
        # Use cached data
        df_easily = pd.DataFrame(st.session_state.easily_data)
        df_lifen = pd.DataFrame(st.session_state.lifen_data) if st.session_state.lifen_data else None
        display_tabs_content(df_easily, df_lifen)
    else:
        # Initial state - no data yet
        render_initial_tabs()

if __name__ == "__main__":
    main()