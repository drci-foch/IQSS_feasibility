import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from app_conf import LIFEN_API_URL
from utils import create_download_link


# Fonction pour récupérer les données Lifen pour les numéros de séjour spécifiés
def get_lifen_data(num_venues, start_date=None, end_date=None):
    """Récupère les données Lifen pour les numéros de séjour spécifiés"""
    try:
        # Filtrer les num_venues valides
        valid_venues = [venue for venue in num_venues if venue and venue != 0]
        if not valid_venues:
            return []

        # Convertir en chaîne pour l'API
        venues_str = ",".join([str(v) for v in valid_venues])

        # Préparer les paramètres de base
        params = {"num_venues": venues_str}

        # Ajouter les dates seulement si elles ne sont pas None
        if start_date is not None and end_date is not None:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date.strftime("%Y-%m-%d")

        # Appeler l'API Lifen avec les paramètres
        response = requests.get(LIFEN_API_URL, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"Erreur lors de la récupération des données Lifen: {response.status_code} - {response.text}"
            )
            return []
    except Exception as e:
        st.error(f"Erreur de connexion à l'API Lifen: {str(e)}")
        return []


# Fonction pour afficher les données Lifen
def display_lifen_data(df_lifen, df_easily):
    if df_lifen.empty:
        st.warning("Aucune donnée Lifen à afficher.")
        return

    st.success(
        f"Requête terminée avec succès !  {len(set(list(df_lifen['num_sej'])))} Lettre de liaison trouvés sur Lifen."
    )

    # Onglets pour organiser l'affichage des données Lifen
    data_tab, stats_tab, charts_tab = st.tabs(
        ["Tableau de données", "Statistiques", "Graphiques"]
    )

    with data_tab:
        st.dataframe(df_lifen, use_container_width=True)

        # Bouton de téléchargement
        st.markdown("<h3>Télécharger les données</h3>", unsafe_allow_html=True)
        st.markdown(
            create_download_link(df_lifen, "diffusion_lifen.csv"),
            unsafe_allow_html=True,
        )

    with stats_tab:
        # Statistiques Lifen
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Nombre total de diffusions", len(df_lifen))

        with col2:
            if "statut_envoi" in df_lifen.columns:
                success_rate = (
                    df_lifen[df_lifen["statut_envoi"] == "Réussite"].shape[0]
                    / len(df_lifen)
                    * 100
                )
                st.metric("Taux de réussite", f"{success_rate:.1f}%")

        with col3:
            if "num_sej" in df_lifen.columns and "Num_Venue" in df_easily.columns:
                coverage = (
                    df_lifen["num_sej"].nunique()
                    / df_easily["Num_Venue"].nunique()
                    * 100
                )
                st.metric("Couverture des séjours", f"{coverage:.1f}%")

        # Distribution par canal
        if "canal_envoi" in df_lifen.columns:
            st.subheader("Distribution par canal")
            channel_counts = df_lifen["canal_envoi"].value_counts().reset_index()
            channel_counts.columns = ["Canal", "Nombre"]
            st.dataframe(channel_counts, use_container_width=True)

        # Distribution par résultat
        if "statut_envoi" in df_lifen.columns:
            st.subheader("Distribution par résultat")
            result_counts = df_lifen["statut_envoi"].value_counts().reset_index()
            result_counts.columns = ["Résultat", "Nombre"]
            st.dataframe(result_counts, use_container_width=True)

        # Distribution par type de destinataire
        if "role_destinataire" in df_lifen.columns:
            st.subheader("Distribution par type de destinataire")
            recipient_counts = (
                df_lifen["role_destinataire"].value_counts().reset_index()
            )
            recipient_counts.columns = ["Type de destinataire", "Nombre"]
            st.dataframe(recipient_counts, use_container_width=True)

    with charts_tab:
        # Graphiques pour les données Lifen
        if "canal_envoi" in df_lifen.columns:
            st.subheader("Répartition par canal")
            fig1 = px.pie(
                df_lifen,
                names="canal_envoi",
                title="Répartition des diffusions par canal",
            )
            st.plotly_chart(fig1, use_container_width=True)

        if "statut_envoi" in df_lifen.columns:
            st.subheader("Répartition par résultat")
            fig2 = px.pie(
                df_lifen,
                names="statut_envoi",
                title="Répartition des diffusions par résultat",
                color_discrete_map={"Réussite": "#8bbc35", "Échec": "#e74c3c"},
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Graphique croisé spécialité vs canal (si les deux dataframes peuvent être liés)
        if (
            "num_sej" in df_lifen.columns
            and "Num_Venue" in df_easily.columns
            and "CR_Doss_spe" in df_easily.columns
        ):
            st.subheader("Canaux par spécialité")
            # Créer un DataFrame enrichi pour ce graphique spécifique
            df_easily_slim = df_easily[["Num_Venue", "CR_Doss_spe"]].rename(
                columns={"Num_Venue": "num_sej"}
            )
            df_enriched = pd.merge(df_lifen, df_easily_slim, on="num_sej", how="left")

            # Créer un graphique à barres empilées
            if (
                "canal_envoi" in df_enriched.columns
                and "CR_Doss_spe" in df_enriched.columns
            ):
                cross_counts = (
                    df_enriched.groupby(["CR_Doss_spe", "canal_envoi"])
                    .size()
                    .reset_index(name="count")
                )
                fig3 = px.bar(
                    cross_counts,
                    x="CR_Doss_spe",
                    y="count",
                    color="canal_envoi",
                    title="Répartition des canaux par spécialité",
                    labels={
                        "CR_Doss_spe": "Spécialité",
                        "count": "Nombre",
                        "canal_envoi": "Canal",
                    },
                )
                st.plotly_chart(fig3, use_container_width=True)
