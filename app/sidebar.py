from datetime import datetime, timedelta

import streamlit as st
from utils import import_venue_numbers


def render_sidebar():
    """Render the sidebar with all selection options"""
    st.markdown("<h2 class='sub-header'>Paramètres de Requête</h2>", unsafe_allow_html=True)

    # Add option to choose between date query and venue import
    query_type = st.radio("Mode de requête", ["Par date", "Par numéros de séjour"], key="sidebar_query_type")

    # Variables to store filter values
    start_date = None
    end_date = None
    imported_venues = []

    # Display relevant section based on user choice
    if query_type == "Par date":
        start_date, end_date = setup_date_filters()
    else:  # Requête par numéros de séjour
        setup_venue_import()
        imported_venues = st.session_state.get("imported_venues", [])

    # Set up advanced filters (same for both query types)
    filter_specialite, filter_result, filter_channel = setup_advanced_filters()

    # Bouton de requête
    st.markdown("<br>", unsafe_allow_html=True)
    run_query = st.button("Exécuter la Requête", type="primary", use_container_width=True, key="sidebar_run_query")

    return (
        query_type,
        start_date,
        end_date,
        imported_venues,
        filter_specialite,
        filter_result,
        filter_channel,
        run_query,
    )


def setup_date_filters():
    """Handle date period selection in the sidebar"""
    st.markdown("<h3>Sélectionner une Période</h3>", unsafe_allow_html=True)
    period_options = [
        "Plage personnalisée",
        "7 derniers jours",
        "30 derniers jours",
        "Dernier trimestre",
        "Année en cours",
    ]
    selected_period = st.selectbox("Période", period_options, key="sidebar_select_period")

    # Gestion de la sélection de date en fonction du choix de période
    if selected_period == "Plage personnalisée":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)  # Par défaut les 30 derniers jours
        start_date = st.date_input("Date de début", value=start_date, key="sidebar_select_start_date")
        end_date = st.date_input("Date de fin", value=end_date, key="sidebar_select_end_date")
    else:
        # Calculer les dates en fonction de la sélection
        end_date = datetime.now().date()

        if selected_period == "7 derniers jours":
            start_date = end_date - timedelta(days=7)
        elif selected_period == "30 derniers jours":
            start_date = end_date - timedelta(days=30)
        elif selected_period == "Dernier trimestre":
            month = end_date.month
            quarter_start_month = 3 * ((month - 1) // 3) + 1
            start_date = datetime(end_date.year, quarter_start_month, 1).date()
        elif selected_period == "Année en cours":
            start_date = datetime(end_date.year, 1, 1).date()

        st.info(f"Période sélectionnée : {start_date.strftime('%d/%m/%Y')} à {end_date.strftime('%d/%m/%Y')}")

    return start_date, end_date


def setup_venue_import():
    """Handle venue number import functionality"""
    st.markdown("<h3>Import de Numéros de Séjour</h3>", unsafe_allow_html=True)

    # No need for expander since this is now a main option
    st.markdown("""
    Vous pouvez importer un fichier contenant des numéros de séjour à ajouter à votre requête.
    Les formats acceptés sont : CSV, Excel (.xls/.xlsx) ou TXT (un numéro par ligne).
    """)

    uploaded_file = st.file_uploader(
        "Choisir un fichier", type=["csv", "xlsx", "xls", "txt"], key="sidebar_file_uploader"
    )

    # Variable pour stocker les numéros de séjour importés
    if "imported_venues" not in st.session_state:
        st.session_state.imported_venues = []

    # Variable pour conserver les numéros de séjour originaux importés
    if "original_imported_venues" not in st.session_state:
        st.session_state.original_imported_venues = []

    if uploaded_file is not None:
        if st.button("Charger les numéros de séjour"):
            # Lire les numéros de séjour du fichier
            imported_venues = import_venue_numbers(uploaded_file)
            st.session_state.imported_venues = imported_venues
            # Sauvegarder la liste originale pour comparaison ultérieure
            st.session_state.original_imported_venues = imported_venues.copy()

            if imported_venues:
                st.success(f"{len(imported_venues)} numéros de séjour importés avec succès.")
                # Afficher un aperçu des premiers numéros
                preview = imported_venues[:5]
                preview_text = ", ".join([str(num) for num in preview])
                if len(imported_venues) > 5:
                    preview_text += f", ... (et {len(imported_venues) - 5} de plus)"
                st.info(f"Aperçu : {preview_text}")
            else:
                st.warning("Aucun numéro de séjour valide trouvé dans le fichier.")

    # Afficher les numéros de séjour importés s'il y en a
    if st.session_state.imported_venues:
        st.text(f"{len(st.session_state.imported_venues)} numéros de séjour détéctés.")

        if st.button("Effacer les numéros importés"):
            st.session_state.imported_venues = []
            st.session_state.original_imported_venues = []
            st.rerun()


def setup_advanced_filters():
    """Set up advanced filters in the sidebar"""
    with st.expander("Filtres avancés", expanded=False):
        # Filtres pour Easily
        st.subheader("Filtres Easily")
        filter_specialite = st.multiselect(
            "Filtrer par spécialité",
            [
                "CARDIOLOGIE",
                "NEUROLOGIE",
                "PNEUMOLOGIE",
                "MEDECINE INTERNE",
                "UROLOGIE",
                "VASCULAIRE",
                "DIGESTIF",
            ],
        )

        # Filtres pour Lifen
        st.subheader("Filtres Lifen")
        filter_result = st.multiselect("Filtrer par résultat", ["Réussite", "Échec"], key="filter_by_result")
        filter_channel = st.multiselect(
            "Filtrer par canal", ["DMP", "MSSANTE", "APICRYPT", "MAIL", "PAPIER"], key="filter_by_channel"
        )

    return filter_specialite, filter_result, filter_channel
