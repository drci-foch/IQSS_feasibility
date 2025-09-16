import streamlit as st
from tabs.analyse import display_analyse_documents
from tabs.easily import display_easily_data
from tabs.lifen import display_lifen_data


def render_initial_tabs():
    """Show initial info in tabs before query execution"""
    easily_tab, lifen_tab, analyse_tab = st.tabs(
        ["Easily (Lettre de liaison)", "Lifen (Diffusion)", "Analyse des délais"]
    )

    with easily_tab:
        st.info(
            "Utilisez la barre latérale pour configurer votre requête, puis cliquez sur 'Exécuter la Requête' "
            "pour voir les résultats."
        )

    with lifen_tab:
        st.info("Les données Lifen seront affichées après l'exécution de la requête Easily.")

    with analyse_tab:
        st.info("L'analyse des délais sera disponible après l'exécution de la requête.")

    return easily_tab, lifen_tab, analyse_tab


def display_tabs_content(df_easily, df_lifen):
    """Display content in each tab based on available data"""
    easily_tab, lifen_tab, analyse_tab = st.tabs(["Source Easily", "Source Lifen", "Comparaison Easily/Lifen"])

    with easily_tab:
        display_easily_data(df_easily)

    with lifen_tab:
        if df_lifen is not None:
            display_lifen_data(df_lifen, df_easily)
        else:
            st.warning("Aucune donnée Lifen disponible pour les numéros de séjour sélectionnés.")

    with analyse_tab:
        if df_lifen is not None:
            display_analyse_documents(df_lifen, df_easily)
        else:
            st.warning("Aucune donnée Lifen disponible pour analyser les délais.")

    # Ajouter le bouton de téléchargement des numéros manquants si disponibles
    if "missing_venues_both" in st.session_state and st.session_state.missing_venues_both:
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
