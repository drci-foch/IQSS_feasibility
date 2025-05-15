import pandas as pd
import streamlit as st
from tabs.easily import get_easily_data
from tabs.lifen import get_lifen_data

def process_data(start_date, end_date, filter_specialite, filter_result, filter_channel):
    """Process data from APIs and apply filters"""
    with st.spinner("Récupération des données..."):
        # Récupérer les données Easily en incluant les numéros de séjour importés
        easily_data = get_easily_data(
            start_date, end_date, st.session_state.imported_venues
        )

        if not easily_data:
            st.warning(
                "Aucune données Easily n'a été retournée. Veuillez vérifier les paramètres de la requête."
            )
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

        # Récupérer les numéros de séjour pour Lifen
        num_venues = (
            df_easily["Num_Venue"].tolist()
            if "Num_Venue" in df_easily.columns
            else []
        )

        # Récupérer les données Lifen correspondantes
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