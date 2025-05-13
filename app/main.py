import base64
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Outil de Requête Comptes-Rendus Patients",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS personnalisé pour améliorer l'apparence
st.markdown(
    """
    <style>
    :root {
        --primary-color: #047dc1;
        --secondary-color: #8bbc35;
        --dark-color: #044c7c;
        --light-color: #f8f9fa;
        --text-color: #333333;
    }
    
    /* Style général */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: var(--primary-color);
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: var(--dark-color);
    }
    .stButton>button {
        width: 100%;
        background-color: var(--primary-color);
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: var(--dark-color);
    }
    .result-container {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        border-left: 4px solid var(--secondary-color);
        background-color: rgba(139, 188, 53, 0.1);
    }
    .highlight {
        color: var(--secondary-color);
        font-weight: bold;
    }
    .card {
        border: 1px solid #e6e6e6;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-top: 3px solid var(--primary-color);
    }
    .info-box {
        background-color: rgba(4, 125, 193, 0.1);
        border-radius: 0.5rem;
        padding: 1rem;
        border-left: 4px solid var(--primary-color);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Configuration des APIs
EASILY_API_URL = os.getenv(
    "EASILY_API_URL", "http://localhost:8000/api/patients/comptes-rendus"
)
LIFEN_API_URL = os.getenv("LIFEN_API_URL", "http://localhost:8001/api/lifen/data")


# Fonction pour lire et extraire les numéros de séjour des fichiers
def import_venue_numbers(uploaded_file):
    """
    Lit un fichier CSV, Excel ou TXT et extrait les numéros de séjour.

    Args:
        uploaded_file: Le fichier téléchargé via st.file_uploader

    Returns:
        list: Liste des numéros de séjour extraits du fichier
    """
    if uploaded_file is None:
        return []

    # Obtenir l'extension du fichier
    file_extension = uploaded_file.name.split(".")[-1].lower()

    try:
        # Traitement selon le type de fichier
        if file_extension == "csv":
            df = pd.read_csv(uploaded_file)
        elif file_extension in ["xls", "xlsx"]:
            df = pd.read_excel(uploaded_file)
        elif file_extension == "txt":
            # Pour les fichiers TXT, on suppose un numéro par ligne
            content = uploaded_file.getvalue().decode("utf-8")
            # Nettoyer et extraire les numéros
            num_venues = [line.strip() for line in content.split("\n") if line.strip()]
            return [int(num) for num in num_venues if num.isdigit()]
        else:
            st.error(f"Format de fichier non pris en charge: {file_extension}")
            return []

        # Pour CSV et Excel, chercher la colonne avec les numéros de séjour
        if "df" in locals():
            # Essayer de deviner la colonne des numéros de séjour
            possible_column_names = [
                "num_venue",
                "num_séjour",
                "numéro_séjour",
                "numéro de séjour",
                "numero_sejour",
                "numero sejour",
                "sejour",
                "séjour",
                "venue",
            ]

            # Vérifier si l'une des colonnes possibles existe dans le dataframe
            found_columns = [
                col
                for col in df.columns
                if col.lower() in [name.lower() for name in possible_column_names]
            ]

            if found_columns:
                # Utiliser la première colonne trouvée
                column_name = found_columns[0]
                # Extraire les numéros et les convertir en entiers si possible
                num_venues = df[column_name].dropna().astype(str).tolist()
                return [int(num) for num in num_venues if str(num).isdigit()]
            elif len(df.columns) == 1:
                # Si une seule colonne, on suppose que c'est celle des numéros de séjour
                num_venues = df.iloc[:, 0].dropna().astype(str).tolist()
                return [int(num) for num in num_venues if str(num).isdigit()]
            else:
                # Si plusieurs colonnes et aucune identifiable, demander à l'utilisateur de choisir
                column_name = st.selectbox(
                    "Sélectionnez la colonne contenant les numéros de séjour:",
                    df.columns,
                )
                num_venues = df[column_name].dropna().astype(str).tolist()
                return [int(num) for num in num_venues if str(num).isdigit()]

        return []

    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier: {str(e)}")
        return []


# Fonction modifiée pour récupérer les données Easily avec filtrage par numéros de séjour
def get_easily_data(start_date, end_date, num_venues=None):
    """Récupère les comptes-rendus patients depuis l'API Easily"""
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


# Fonction pour récupérer les données Lifen pour les numéros de séjour spécifiés
def get_lifen_data(num_venues, start_date, end_date):
    """Récupère les données Lifen pour les numéros de séjour spécifiés"""
    try:
        # Filtrer les num_venues valides
        valid_venues = [venue for venue in num_venues if venue and venue != 0]

        if not valid_venues:
            return []

        # Convertir en chaîne pour l'API
        venues_str = ",".join([str(v) for v in valid_venues])

        # Appeler l'API Lifen avec les numéros de séjour
        response = requests.get(
            LIFEN_API_URL,
            params={
                "num_venues": venues_str,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
        )

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


# Fonction pour exporter des données en CSV
def create_download_link(df, filename):
    """Crée un lien de téléchargement pour un DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="highlight">Télécharger {filename}</a>'
    return href


def main():
    # En-tête
    st.markdown(
        "<h1 class='main-header'>Outil de Requête Comptes-Rendus Patients</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Un outil pour analyser les comptes-rendus patients validés et leur diffusion via Lifen."
    )

    # Barre latérale pour les configurations
    with st.sidebar:
        st.markdown(
            "<h2 class='sub-header'>Paramètres de Requête</h2>", unsafe_allow_html=True
        )

        # Sélection de la période
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
            start_date = end_date - timedelta(
                days=30
            )  # Par défaut les 30 derniers jours
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

            st.info(
                f"Période sélectionnée : {start_date.strftime('%d/%m/%Y')} à {end_date.strftime('%d/%m/%Y')}"
            )

        # Ajout du module d'importation de numéros de séjour
        st.markdown("<h3>Importation de Numéros de Séjour</h3>", unsafe_allow_html=True)
        with st.expander("Importer des numéros de séjour", expanded=False):
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

            if uploaded_file is not None:
                if st.button("Charger les numéros de séjour"):
                    # Lire les numéros de séjour du fichier
                    imported_venues = import_venue_numbers(uploaded_file)
                    st.session_state.imported_venues = imported_venues

                    if imported_venues:
                        st.success(
                            f"{len(imported_venues)} numéros de séjour importés avec succès."
                        )
                        # Afficher un aperçu des premiers numéros
                        preview = imported_venues[:5]
                        preview_text = ", ".join([str(num) for num in preview])
                        if len(imported_venues) > 5:
                            preview_text += (
                                f", ... (et {len(imported_venues) - 5} de plus)"
                            )
                        st.info(f"Aperçu : {preview_text}")
                    else:
                        st.warning(
                            "Aucun numéro de séjour valide trouvé dans le fichier."
                        )

            # Afficher les numéros de séjour importés s'il y en a
            if st.session_state.imported_venues:
                st.text(
                    f"{len(st.session_state.imported_venues)} numéros de séjour seront inclus dans la requête."
                )

                if st.button("Effacer les numéros importés"):
                    st.session_state.imported_venues = []
                    st.rerun()

        # Filtres supplémentaires dans un expander
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
            filter_result = st.multiselect(
                "Filtrer par résultat", ["Réussite", "Échec"], key="filter_by_result"
            )
            filter_channel = st.multiselect(
                "Filtrer par canal", ["DMP", "MSSANTE", "APICRYPT", "MAIL", "PAPIER"], key="filter_by_channel"
            )

        # Bouton de requête
        st.markdown("<br>", unsafe_allow_html=True)
        run_query = st.button(
            "Exécuter la Requête", type="primary", use_container_width=True
        )

    # Zone de contenu principal avec onglets pour Easily et Lifen
    easily_tab, lifen_tab, analyse_tab = st.tabs(
        ["Easily (Comptes-rendus)", "Lifen (Diffusion)", "Analyse des délais"]
    )

    # Variables pour stocker les données entre les onglets
    if "easily_data" not in st.session_state:
        st.session_state.easily_data = None
    if "lifen_data" not in st.session_state:
        st.session_state.lifen_data = None

    if run_query:
        with st.spinner("Récupération des données..."):
            # Récupérer les données Easily en incluant les numéros de séjour importés
            easily_data = get_easily_data(
                start_date, end_date, st.session_state.imported_venues
            )

            if easily_data:
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

                # Afficher les résultats dans les onglets respectifs
                with easily_tab:
                    display_easily_data(df_easily)

                with lifen_tab:
                    if lifen_data:
                        display_lifen_data(df_lifen, df_easily)
                    else:
                        st.warning(
                            "Aucune donnée Lifen disponible pour les numéros de séjour sélectionnés."
                        )

                with analyse_tab:
                    if lifen_data:
                        display_analyse_documents(df_lifen, df_easily)
                    else:
                        st.warning(
                            "Aucune donnée Lifen disponible pour analyser les délais."
                        )
            else:
                st.warning(
                    "Aucune donnée Easily n'a été retournée. Veuillez vérifier les paramètres de la requête."
                )
    else:
        # Affichage initial si les données sont déjà chargées
        if st.session_state.easily_data:
            df_easily = pd.DataFrame(st.session_state.easily_data)

            with easily_tab:
                display_easily_data(df_easily)

            if st.session_state.lifen_data:
                df_lifen = pd.DataFrame(st.session_state.lifen_data)

                with lifen_tab:
                    display_lifen_data(df_lifen, df_easily)

                with analyse_tab:
                    display_analyse_documents(df_lifen, df_easily)
        else:
            # Message initial
            with easily_tab:
                st.info(
                    "Utilisez la barre latérale pour configurer votre requête, puis cliquez sur 'Exécuter la Requête' pour voir les résultats."
                )

            with lifen_tab:
                st.info(
                    "Les données Lifen seront affichées après l'exécution de la requête Easily."
                )

            with analyse_tab:
                st.info(
                    "L'analyse des délais sera disponible après l'exécution de la requête."
                )


# Fonction pour afficher les données Easily
def display_easily_data(df):
    if df.empty:
        st.warning("Aucune donnée à afficher.")
        return

    st.success(f"Requête terminée avec succès ! {len(df)} comptes-rendus trouvés.")

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
            st.metric("Nombre total de comptes-rendus", len(df))

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
                title="Répartition des comptes-rendus par spécialité",
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


# Fonction pour afficher les données Lifen
def display_lifen_data(df_lifen, df_easily):
    if df_lifen.empty:
        st.warning("Aucune donnée Lifen à afficher.")
        return

    st.success(
        f"Données Lifen récupérées avec succès ! {len(df_lifen)} enregistrements trouvés."
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


def display_analyse_documents(df_lifen, df_easily):
    st.header("Analyse des délais entre validation, sortie et envoi")

    st.markdown("""
Cette analyse porte sur la différence entre la date de sortie du patient et la date d'envoi du document via Lifen.

- Les dates utilisées pour cette analyse correspondent aux dates d'envoi les plus anciennes.

- Seules les données où le champ role_destinataire est égal à "Patient" dans Lifen ont été prises en compte.
    """)

    st.info(
        "Il est possible de télécharger le document utilisé pour l'analyse en bas de page."
    )

    # Filtrage et renommage des colonnes pour Easily

    df_easily = df_easily[
        [
            "pat_IPP",
            "Num_Venue",
            "ven_theo",
            "sej_date_entree",
            "sej_date_sortie",
            "CR_Doss_spe",
            "date_min_val",
            "LL_J0",
        ]
    ]
    df_easily.rename(
        columns={
            "pat_IPP": "ipp",
            "Num_Venue": "num_sej",
            "ven_theo": "ven_theo_easily",
            "sej_date_entree": "date_entree_easily",
            "sej_date_sortie": "date_sortie_easily",
            "CR_Doss_spe": "specialite_easily",
            "date_min_val": "date_min_val_easily",
            "LL_J0": "ll_j0_easily",
        },
        inplace=True,
    )

    # Filtrage et renommage des colonnes pour Lifen
    df_lifen.rename(
        columns={
            "ipp": "ipp",
            "num_sej": "num_sej",
            "date_sortie": "date_sortie_lifen",
            "date_envoi": "date_envoi_lifen",
            "role_destinataire": "role_destinataire",
            "type_sej": "specialite_lifen",
        },
        inplace=True,
    )
    df_lifen = df_lifen[
        [
            "ipp",
            "num_sej",
            "date_sortie_lifen",
            "specialite_lifen",
            "date_envoi_lifen",
            "role_destinataire",
        ]
    ]
    df_lifen = df_lifen[df_lifen["role_destinataire"] == "Patient"]

    # Extraction du premier document envoyé par séjour
    df_min_lifen = (
        df_lifen.sort_values("date_envoi_lifen")
        .groupby(["num_sej"])
        .first()
        .reset_index()
    )

    # Jointure des données
    df_merge = df_min_lifen.merge(df_easily, on=["ipp", "num_sej"])

    # Conversion des colonnes de date
    df_merge["date_envoi_lifen"] = pd.to_datetime(
        df_merge["date_envoi_lifen"], errors="coerce"
    )
    df_merge["date_sortie_easily"] = pd.to_datetime(
        df_merge["date_sortie_easily"], errors="coerce"
    )

    # Calcul des différences de date
    df_merge["diff_date_envoi_date_sortie_lifen"] = (
        df_merge["date_envoi_lifen"] - df_merge["date_sortie_easily"]
    ).dt.days

    # Affichage des résultats
    st.subheader("Distribution des délais envoi-sortie (Lifen)")
    fig = px.histogram(
        df_merge,
        x="diff_date_envoi_date_sortie_lifen",
        title="Distribution des délais envoi-sortie (Lifen)",
        nbins=100,
        labels={"diff_date_envoi_date_sortie_lifen": "Délai (jours)"},
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Analyse des documents avec délai important
    seuil_ecart = st.slider(
        "Sélectionner un seuil d'écart (en jours)", min_value=0, max_value=100, value=30
    )
    df_large_gap = df_merge[df_merge["diff_date_envoi_date_sortie_lifen"] > seuil_ecart]

    st.subheader(f"Documents avec un écart supérieur à {seuil_ecart} jours")
    if not df_large_gap.empty:
        st.dataframe(df_large_gap)

    # Téléchargement des résultats
    st.markdown("### Télécharger les résultats")
    csv = df_merge.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="analyse_documents.csv">Télécharger le fichier CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

    # Pied de page
    st.markdown("---")
    st.markdown("© 2025 - Outil de Requête Comptes-Rendus Patients et Diffusion v1.0")


if __name__ == "__main__":
    main()
