import pandas as pd
import streamlit as st
from tabs.easily import get_easily_data
from tabs.lifen import get_lifen_data


def process_data(query_type=None, start_date=None, end_date=None, imported_venues=None, filter_specialite=None, filter_result=None, filter_channel=None):
    """Process data from APIs and apply filters based on query type"""
    with st.spinner("Récupération des données..."):
        # Determine query mode
        is_venue_query = query_type == "Requête par numéros de séjour"

        # Réinitialiser les listes des numéros non trouvés
        st.session_state.missing_venues_easily = []
        st.session_state.missing_venues_lifen = []
        st.session_state.missing_venues_both = []

        if is_venue_query:
            # Pour les requêtes par numéros de séjour, utiliser null pour les dates
            # et s'assurer que nous avons des numéros de séjour valides
            if not imported_venues or len(imported_venues) == 0:
                st.warning("Aucun numéro de séjour importé. Veuillez importer des numéros de séjour.")
                return None, None

            # Récupérer les données Easily en mode venue uniquement
            easily_data = get_easily_data(
                start_date=None,
                end_date=None,
                venue_numbers=imported_venues
            )

            # Pour une requête par numéro de séjour, utiliser directement les numéros importés
            num_venues = imported_venues

            # Récupérer les données Lifen avec les numéros de séjour importés
            lifen_data = get_lifen_data(num_venues, None, None)

            # Identifier les numéros de séjour retrouvés dans Easily
            found_venues_easily = set()
            if easily_data:
                for item in easily_data:
                    if "Num_Venue" in item and item["Num_Venue"]:
                        try:
                            found_venues_easily.add(int(item["Num_Venue"]))
                        except (ValueError, TypeError):
                            pass

            # Identifier les numéros de séjour retrouvés dans Lifen
            found_venues_lifen = set()
            if lifen_data:
                for item in lifen_data:
                    if "num_sej" in item and item["num_sej"]:
                        try:
                            found_venues_lifen.add(int(item["num_sej"]))
                        except (ValueError, TypeError):
                            pass

            # Comparer avec la liste originale des numéros importés
            original_venues = set(st.session_state.original_imported_venues)

            # Numéros manquants dans Easily
            missing_venues_easily = original_venues - found_venues_easily
            st.session_state.missing_venues_easily = sorted(list(missing_venues_easily))

            # Numéros manquants dans Lifen
            missing_venues_lifen = original_venues - found_venues_lifen
            st.session_state.missing_venues_lifen = sorted(list(missing_venues_lifen))

            # Numéros manquants dans les deux systèmes
            missing_venues_both = missing_venues_easily.intersection(missing_venues_lifen)
            st.session_state.missing_venues_both = sorted(list(missing_venues_both))

            if missing_venues_both:
                st.info(f"{len(missing_venues_both)} numéros de séjour n'ont été retrouvés ni dans Easily ni dans Lifen.")

        else:
            # Pour les requêtes par date, utiliser les dates sélectionnées
            # et ignorer les numéros de séjour
            if not start_date or not end_date:
                st.warning("Veuillez sélectionner des dates valides pour la requête.")
                return None, None
            # Récupérer les données Easily avec les dates
            easily_data = get_easily_data(
                start_date=start_date,
                end_date=end_date,
                venue_numbers=[]  # Liste vide pour les requêtes par date
            )


        if not easily_data:
            message = "Aucune donnée Easily n'a été retournée."
            if is_venue_query:
                message += " Vérifiez les numéros de séjour importés."
            else:
                message += " Vérifiez les dates sélectionnées."
            st.warning(message)
            return None, None

        # Store in session state
        st.session_state.easily_data = easily_data

        # Convertir en DataFrame pour faciliter la manipulation
        df_easily = pd.DataFrame(easily_data)

        # Appliquer les filtres Easily
        if filter_specialite:
            df_easily = df_easily[
                df_easily["CR_Doss_spe"].isin(filter_specialite)
            ]

        # MODIFICATION ICI: Déterminer quels numéros de séjour utiliser pour Lifen
        if is_venue_query:
            # Pour une requête par numéro de séjour, utiliser directement les numéros importés
            # au lieu d'extraire les numéros depuis la réponse Easily
            num_venues = imported_venues

            # Récupérer les données Lifen avec les numéros de séjour importés
            lifen_data = get_lifen_data(num_venues, None, None)
        else:
            # Pour une requête par date, extraire les numéros de séjour depuis la réponse Easily
            num_venues = (
                df_easily["Num_Venue"].tolist()
                if "Num_Venue" in df_easily.columns
                else []
            )

            # Récupérer les données Lifen avec les dates et les numéros extraits d'Easily
            lifen_data = get_lifen_data(num_venues, start_date, end_date)

        # Store in session state
        st.session_state.lifen_data = lifen_data

        # Créer un DataFrame Lifen
        if lifen_data:
            df_lifen = pd.DataFrame(lifen_data)
            # Appliquer les filtres Lifen
            if filter_result and "statut_envoi" in df_lifen.columns:
                df_lifen = df_lifen[
                    df_lifen["statut_envoi"].isin(filter_result)
                ]
            if filter_channel and "canal_envoi" in df_lifen.columns:
                df_lifen = df_lifen[
                    df_lifen["canal_envoi"].isin(filter_channel)
                ]
        else:
            df_lifen = None

    return df_easily, df_lifen
