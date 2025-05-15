import plotly.express as px
import requests
import streamlit as st
from app_conf import EASILY_API_URL
from utils import create_download_link


# Fonction pour afficher les données Easily
def display_easily_data(df):
    if df.empty:
        st.warning("Aucune donnée à afficher.")
        return

    st.success(f"Requête terminée avec succès ! {len(df)} Lettre de liaison trouvés.")

    # Onglets pour organiser l'affichage des données Easily
    data_tab, stats_tab, charts_tab = st.tabs(
        ["Tableau de données", "Statistiques", "Graphiques"]
    )

    with data_tab:
        st.dataframe(df, use_container_width=True)

        # Bouton de téléchargement
        st.markdown("<h3>Télécharger les données</h3>", unsafe_allow_html=True)
        st.markdown(
            create_download_link(df, "comptes_rendus_easily.csv"),
            unsafe_allow_html=True,
        )

    with stats_tab:
        # Statistiques Easily
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Nombre total de Lettre de liaison", len(df))

        with col2:
            if "pat_IPP" in df.columns:
                st.metric("Patients uniques", df["pat_IPP"].nunique())

        with col3:
            if "LL_J0" in df.columns:
                delay = df["LL_J0"].mean()
                st.metric("Délai moyen de validation (jours)", f"{delay:.1f}")

        # Distribution par spécialité
        if "CR_Doss_spe" in df.columns:
            st.subheader("Distribution par spécialité")
            specialty_counts = df["CR_Doss_spe"].value_counts().reset_index()
            specialty_counts.columns = ["Spécialité", "Nombre"]
            st.dataframe(specialty_counts, use_container_width=True)

        # Distribution par mois
        if "mois" in df.columns:
            st.subheader("Distribution par mois")
            month_counts = df["mois"].value_counts().reset_index()
            month_counts.columns = ["Mois", "Nombre"]
            st.dataframe(month_counts, use_container_width=True)

    with charts_tab:
        # Graphiques pour les données Easily
        if "CR_Doss_spe" in df.columns:
            st.subheader("Répartition par spécialité")
            fig1 = px.pie(
                df,
                names="CR_Doss_spe",
                title="Répartition des Lettre de liaison par spécialité",
            )
            st.plotly_chart(fig1, use_container_width=True)

        if "LL_J0" in df.columns:
            st.subheader("Délai de validation")
            fig2 = px.histogram(
                df,
                x="LL_J0",
                nbins=20,
                title="Distribution des délais de validation (en jours)",
                labels={"LL_J0": "Délai de validation (jours)"},
                color_discrete_sequence=["#047dc1"],
            )
            st.plotly_chart(fig2, use_container_width=True)

        if "nuit_1" in df.columns:
            st.subheader("Durée des séjours")
            fig3 = px.histogram(
                df,
                x="nuit_1",
                nbins=50,
                title="Distribution des durées de séjour (en nuits)",
                labels={"nuit_1": "Durée de séjour (nuits)"},
                color_discrete_sequence=["#8bbc35"],
            )
            st.plotly_chart(fig3, use_container_width=True)


# Fonction modifiée pour récupérer les données Easily avec filtrage par numéros de séjour
def get_easily_data(start_date, end_date, num_venues=None):
    """Récupère les Lettre de liaison patients depuis l'API Easily"""
    try:
        # Préparer les paramètres de base
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }

        # Ajouter les numéros de séjour s'ils sont spécifiés
        if num_venues and len(num_venues) > 0:
            # Convertir la liste de numéros en chaîne pour l'API
            params["venues"] = ",".join([str(v) for v in num_venues])

        # Appeler l'API avec les paramètres
        response = requests.get(EASILY_API_URL, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"Erreur lors de la récupération des données Easily: {response.status_code} - {response.text}"
            )
            return []
    except Exception as e:
        st.error(f"Erreur de connexion à l'API Easily: {str(e)}")
        return []
