from datetime import datetime, timedelta

import streamlit as st
from utils import import_venue_numbers


def render_sidebar():
    """Render the sidebar with all selection options"""
    st.markdown("<h2 class='sub-header'>Requête</h2>", unsafe_allow_html=True)

    # Add option to choose between date query and venue import
    query_type = st.radio("", ["Par date", "Par numéros de séjour"], key="sidebar_query_type")

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

    # Validation finale seulement quand l'utilisateur clique sur le bouton
    if run_query:
        # Validation pour les requêtes par date
        if query_type == "Par date":
            if start_date is None or end_date is None:
                st.error("❌ Veuillez saisir des dates valides au format JJ/MM/AAAA")
                run_query = False
            elif start_date > end_date:
                st.error("❌ La date de début doit être antérieure à la date de fin")
                run_query = False

        # Validation pour les requêtes par numéros de séjour
        elif query_type == "Par numéros de séjour":
            if not imported_venues or len(imported_venues) == 0:
                st.error("❌ Veuillez importer des numéros de séjour avant d'exécuter la requête")
                run_query = False

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
    """Handle date period selection with form to avoid re-runs"""
    st.markdown("<h3>Sélectionner une période</h3>", unsafe_allow_html=True)
    period_options = [
        "Plage personnalisée",
        "7 derniers jours",
        "30 derniers jours",
        "Dernier trimestre",
        "Année en cours",
    ]
    selected_period = st.selectbox("Période", period_options, key="sidebar_select_period")

    if selected_period == "Plage personnalisée":
        # Utiliser un formulaire pour éviter les re-runs
        with st.form("custom_date_form", clear_on_submit=False):
            # Dates par défaut
            default_end = datetime.now().date()
            default_start = default_end - timedelta(days=30)

            col1, col2 = st.columns(2)

            with col1:
                start_date_str = st.text_input(
                    "Début",
                    value=default_start.strftime("%d/%m/%Y"),
                    placeholder="JJ/MM/AAAA",
                    help="Format: JJ/MM/AAAA",
                )

            with col2:
                end_date_str = st.text_input(
                    "Fin", value=default_end.strftime("%d/%m/%Y"), placeholder="JJ/MM/AAAA", help="Format: JJ/MM/AAAA"
                )

            # Bouton de validation du formulaire
            submitted = st.form_submit_button("Valider les dates", type="secondary", use_container_width=False)

            if submitted:
                try:
                    start_date = datetime.strptime(start_date_str, "%d/%m/%Y").date()
                    end_date = datetime.strptime(end_date_str, "%d/%m/%Y").date()

                    if start_date <= end_date:
                        st.session_state.custom_start_date = start_date
                        st.session_state.custom_end_date = end_date
                        duration = (end_date - start_date).days
                        st.success(f"✅ Dates validées: {duration} jours")
                    else:
                        st.error("❌ La date de début doit être antérieure à la date de fin")
                except ValueError:
                    st.error("❌ Format de date invalide. Utilisez JJ/MM/AAAA")

        # Utiliser les dates validées ou les valeurs par défaut
        start_date = getattr(st.session_state, "custom_start_date", default_start)
        end_date = getattr(st.session_state, "custom_end_date", default_end)

        # Affichage des dates actuellement sélectionnées
        if hasattr(st.session_state, "custom_start_date"):
            duration = (end_date - start_date).days
            st.info(
                f"📅 Période sélectionnée: {duration} jours  \nDu {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
            )

    else:
        # Calcul automatique des dates selon la période
        end_date = datetime.now().date()
        if selected_period == "7 derniers jours":
            start_date = end_date - timedelta(days=7)
        elif selected_period == "30 derniers jours":
            start_date = end_date - timedelta(days=30)
        elif selected_period == "Dernier trimestre":
            start_date = end_date - timedelta(days=90)
        elif selected_period == "Année en cours":
            start_date = datetime(end_date.year, 1, 1).date()

        # Réinitialiser les dates personnalisées si on change de mode
        if hasattr(st.session_state, "custom_start_date"):
            del st.session_state.custom_start_date
            del st.session_state.custom_end_date

        # Affichage des dates sélectionnées en format DD/MM/YYYY
        st.info(f"📅 **{selected_period}**  \nDu {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}")

    return start_date, end_date


def setup_venue_import():
    """Handle venue number import functionality"""
    st.markdown("<h3>Importer Numéros de Séjour</h3>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choisir un fichier Excel",
        type=["xlsx", "xls"],
        help="Le fichier doit contenir une colonne avec les numéros de séjour",
        key="venue_uploader",
    )

    if uploaded_file:
        try:
            # Import venue numbers (assuming this function exists in utils)
            venues = import_venue_numbers(uploaded_file)
            st.session_state.imported_venues = venues
            st.success(f"✅ {len(venues)} numéros de séjour importés avec succès")
        except Exception as e:
            st.error(f"❌ Erreur lors de l'import: {str(e)}")

    # Afficher les numéros de séjour importés s'il y en a
    if st.session_state.get("imported_venues"):
        st.text(f"{len(st.session_state.imported_venues)} numéros de séjour détectés.")

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
            placeholder="Sélectionner une ou plusieurs spécialités",
        )

        # Filtres pour Lifen
        st.subheader("Filtres Lifen")
        filter_result = st.multiselect(
            "Filtrer par résultat",
            ["Réussite", "Échec"],
            key="filter_by_result",
            placeholder="Sélectionner un ou plusieurs résultats",
        )
        filter_channel = st.multiselect(
            "Filtrer par canal",
            ["DMP", "MSSANTE", "APICRYPT", "MAIL", "PAPIER"],
            key="filter_by_channel",
            placeholder="Sélectionner un ou plusieurs canaux",
        )

    return filter_specialite, filter_result, filter_channel
