
import pandas as pd
import streamlit as st
from data_processor import process_data

# Import modular components
from sidebar import render_sidebar
from style import custom_css
from tabs_handler import display_tabs_content, render_initial_tabs

st.set_page_config(
    page_title="QualiFoch",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(custom_css, unsafe_allow_html=True)


def main():
    # En-tête
    st.markdown(
        """
        <style>
            .main-header {
                font-size: 2.5em;
                font-weight: bold;
                text-align: center;
                color: #2c3e50;
                margin-bottom: 20px;
            }
            .description {
                font-size: 1.2em;
                line-height: 1.6;
                color: #34495e;
                text-align: center;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 class='main-header'>SEQUAD : Sécurité, Évaluation et Qualité des Données </h1>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <p class='description'>
            SEQUAD est un outil dédié à l'analyse des lettres de liaison patients validées,
            ainsi qu'à leur diffusion sécurisée via Lifen.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "easily_data" not in st.session_state:
        st.session_state.easily_data = None
    if "lifen_data" not in st.session_state:
        st.session_state.lifen_data = None

    # Render sidebar and get user selections
    with st.sidebar:
        query_type, start_date, end_date, imported_venues, filter_specialite, filter_result, filter_channel, run_query = render_sidebar()

    # Process data if requested or display cached data
    if run_query:
        # Call process_data with all parameters from sidebar
        df_easily, df_lifen = process_data(
            query_type=query_type,
            start_date=start_date,
            end_date=end_date,
            imported_venues=imported_venues,
            filter_specialite=filter_specialite,
            filter_result=filter_result,
            filter_channel=filter_channel
        )

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
