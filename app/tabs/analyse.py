import base64

import pandas as pd
import plotly.express as px
import streamlit as st


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

    # Modification de la logique: au lieu de prendre la première date d'envoi,
    # on fait d'abord un merge pour avoir accès à date_sortie_easily
    df_temp = df_lifen.merge(df_easily[["ipp", "num_sej", "date_sortie_easily"]], on=["ipp", "num_sej"])

    # Calculer la différence absolue entre date_envoi_lifen et date_sortie_easily
    df_temp["diff_date"] = abs(pd.to_datetime(df_temp["date_envoi_lifen"]) -
                               pd.to_datetime(df_temp["date_sortie_easily"]))

    # Sélectionner pour chaque num_sej la ligne avec la plus petite différence
    df_min_lifen = df_temp.sort_values("diff_date").groupby("num_sej").first().reset_index()

    # On ne garde que les colonnes originales de df_lifen pour le merge final
    df_min_lifen = df_min_lifen[["ipp", "num_sej", "date_sortie_lifen", "specialite_lifen",
                                 "date_envoi_lifen", "role_destinataire"]]

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
    st.markdown("© 2025 - Outil de Requête Lettre de liaison Patients et Diffusion v1.0")
