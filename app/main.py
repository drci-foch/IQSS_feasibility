import pandas as pd
import streamlit as st

# Import du module d'authentification
from auth import check_permission, render_login_page, render_user_info, is_logged_in
from data_processor import process_data

# Import modular components
from sidebar import render_sidebar
from style import custom_css
from streamlit_javascript import st_javascript
import time

st.set_page_config(
    page_title="SEQUAD - Système d'Authentification",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    # Vérifier l'authentification
    token = st_javascript("""(() => {
        return window.localStorage.getItem('access_token');
    })()""")
    st.session_state["access_token"] = token
    if not is_logged_in():
        render_login_page()
        return

    # Afficher les informations utilisateur dans la sidebar
    render_user_info()

    # CSS pour sidebar redimensionnable et styles du header
    st.markdown(
        """
        <style>
            .logo-container {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo-container img {
                height: 150px;
                width: auto;
                object-fit: contain;
            }
            .main-header {
                font-size: 3em;
                font-weight: bold;
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
            }
            .description {
                font-size: 1.4em;
                line-height: 1.6;
                color: #34495e;
                text-align: center;
                max-width: 800px;
                margin: 0 auto;
            }
            .permission-warning {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 1rem;
                margin: 1rem 0;
                color: #856404;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header simple avec logo centré
    st.markdown(
        """
        <div class="logo-container">
            <img src="https://upload.wikimedia.org/wikipedia/fr/d/d4/Logo_HOPITAL_FOCH.png" 
                 alt="Logo Hôpital Foch" 
                 onerror="this.style.display='none'">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 class='main-header'>SEQUAD : Sécurité, Évaluation et Qualité des Données</h1>",
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "easily_data" not in st.session_state:
        st.session_state.easily_data = None
    if "lifen_data" not in st.session_state:
        st.session_state.lifen_data = None

    # Vérifier les permissions avant d'afficher la sidebar
    if not check_permission("easily"):
        st.markdown(
            """
            <div class="permission-warning">
                ⚠️ <strong>Accès limité</strong><br>
                Votre compte n'a pas les permissions nécessaires pour accéder aux données Easily.
                Contactez l'administrateur pour obtenir les accès requis.
            </div>
        """,
            unsafe_allow_html=True,
        )
        return

    # Render sidebar and get user selections
    with st.sidebar:
        # Afficher seulement si l'utilisateur a les permissions Easily
        if check_permission("easily"):
            (
                query_type,
                start_date,
                end_date,
                imported_venues,
                filter_specialite,
                filter_result,
                filter_channel,
                run_query,
            ) = render_sidebar()
        else:
            st.warning("❌ Accès aux requêtes non autorisé")
            return

    # Process data if requested or display cached data
    if run_query:
        # Vérifier les permissions avant de traiter les données
        if not check_permission("easily"):
            st.error("❌ Vous n'avez pas l'autorisation d'accéder aux données Easily")
            return

        # Call process_data with all parameters from sidebar
        df_easily, df_lifen = process_data(
            query_type=query_type,
            start_date=start_date,
            end_date=end_date,
            imported_venues=imported_venues,
            filter_specialite=filter_specialite,
            filter_result=filter_result,
            filter_channel=filter_channel,
        )

        if df_easily is not None:
            display_tabs_content_with_permissions(df_easily, df_lifen)

    elif st.session_state.easily_data:
        # Use cached data
        df_easily = pd.DataFrame(st.session_state.easily_data)
        df_lifen = pd.DataFrame(st.session_state.lifen_data) if st.session_state.lifen_data else None
        display_tabs_content_with_permissions(df_easily, df_lifen)
    else:
        # Initial state - no data yet
        render_initial_tabs_with_permissions()


def display_tabs_content_with_permissions(df_easily, df_lifen):
    """Display content in each tab based on available data and user permissions"""

    # Créer les onglets selon les permissions
    tabs_config = []

    if check_permission("easily"):
        tabs_config.append("Source Easily")

    if check_permission("lifen"):
        tabs_config.append("Source Lifen")

    if check_permission("analysis"):
        tabs_config.append("Comparaison Easily/Lifen")

    if not tabs_config:
        st.error("❌ Aucune permission d'accès aux données")
        return

    tabs = st.tabs(tabs_config)
    tab_index = 0

    # Onglet Easily
    if check_permission("easily"):
        with tabs[tab_index]:
            from tabs.easily import display_easily_data

            display_easily_data(df_easily)
        tab_index += 1

    # Onglet Lifen
    if check_permission("lifen"):
        with tabs[tab_index]:
            if df_lifen is not None:
                from tabs.lifen import display_lifen_data

                display_lifen_data(df_lifen, df_easily)
            else:
                st.warning("Aucune donnée Lifen disponible pour les numéros de séjour sélectionnés.")
        tab_index += 1

    # Onglet Analyse
    if check_permission("analysis"):
        with tabs[tab_index]:
            if df_lifen is not None:
                from tabs.analyse import display_analyse_documents

                display_analyse_documents(df_lifen, df_easily)
            else:
                st.warning("Aucune donnée Lifen disponible pour analyser les délais.")

    # Ajouter le bouton de téléchargement des numéros manquants si disponibles et autorisé
    if (
        check_permission("easily")
        and "missing_venues_both" in st.session_state
        and st.session_state.missing_venues_both
    ):
        missing_count = len(st.session_state.missing_venues_both)

        # Créer une colonne pour le bouton
        col1, col2 = st.columns([3, 1])

        with col1:
            st.warning(f"{missing_count} numéros de séjour n'ont été retrouvés ni dans Easily ni dans Lifen.")

        with col2:
            # Convertir la liste en CSV
            csv_content = "numero_sejour\n" + "\n".join(map(str, st.session_state.missing_venues_both))

            # Créer un bouton de téléchargement
            st.download_button(
                label="Télécharger",
                data=csv_content,
                file_name="numeros_sejour_absents_partout.csv",
                mime="text/csv",
            )


def render_initial_tabs_with_permissions():
    """Show initial info in tabs before query execution based on permissions"""

    # Créer les onglets selon les permissions
    tabs_config = []

    if check_permission("easily"):
        tabs_config.append("Easily (Lettre de liaison)")

    if check_permission("lifen"):
        tabs_config.append("Lifen (Diffusion)")

    if check_permission("analysis"):
        tabs_config.append("Analyse des délais")

    if not tabs_config:
        st.error("❌ Aucune permission d'accès aux données")
        return

    tabs = st.tabs(tabs_config)
    tab_index = 0

    if check_permission("easily"):
        with tabs[tab_index]:
            st.info(
                "Utilisez la barre latérale pour configurer votre requête, puis cliquez sur 'Exécuter la Requête' "
                "pour visualiser les résultats."
            )
        tab_index += 1

    if check_permission("lifen"):
        with tabs[tab_index]:
            if check_permission("easily"):
                st.info("Les données Lifen seront affichées après l'exécution de la requête Easily.")
            else:
                st.warning("❌ Accès aux données Easily requis pour utiliser Lifen")
        tab_index += 1

    if check_permission("analysis"):
        with tabs[tab_index]:
            if check_permission("easily") and check_permission("lifen"):
                st.info("L'analyse des délais sera disponible après l'exécution de la requête.")
            else:
                st.warning("❌ Accès aux données Easily et Lifen requis pour les analyses")


if __name__ == "__main__":
    main()
