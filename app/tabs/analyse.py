import base64

import pandas as pd
import plotly.express as px
import streamlit as st


def display_analyse_documents(df_lifen, df_easily):
    st.header("Analyse des délais entre validation, sortie et envoi")
    st.markdown("""
## Objectif de l'analyse
Cette analyse vous permet d'évaluer les délais de transmission des lettres de liaison aux patients à travers trois mesures clés :

1. **Délai global** : Temps écoulé entre la date de sortie du patient et la date d'envoi du document via Lifen.
2. **Délai pour lettres validées le jour de la sortie** : Focus sur les lettres validées exactement le jour de sortie du patient, permettant d'évaluer l'efficacité du processus idéal.
3. **Délai depuis la validation médicale** : Temps écoulé entre la validation par le médecin et l'envoi effectif du document, indépendamment de la date de sortie.

## Filtres appliqués
- Seuls les documents destinés aux patients (rôle_destinataire = "Patient" dans Lifen) sont analysés.
- Les lettres validées plus de 3 jours avant la sortie sont exclues pour éviter les biais.
- Pour chaque séjour, seul l'envoi le plus proche de la date de sortie est conservé.
- L'archivage des données Lifen remonte jusqu'au 01/01/2023.

Ces statistiques permettent d'identifier les étapes du processus qui peuvent être optimisées pour améliorer les délais d'envoi.
    """)
    st.info(
        "Il est possible de télécharger le document utilisé pour l'analyse en bas de page."
    )


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
            "Date diffusion",
            "fiche_id"

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
            "Date diffusion": "date_diffusion_easily",

        },
        inplace=True,
    )

    df_easily.drop_duplicates(inplace=True)



    # Convertir les dates en format datetime pour pouvoir calculer les différences
    df_easily['date_sortie_dt'] = pd.to_datetime(df_easily['date_sortie_easily'])
    df_easily['date_diffusion_dt'] = pd.to_datetime(df_easily['date_diffusion_easily'], format='%d/%m/%Y')

    # Calculer la différence absolue entre les deux dates
    df_easily['time_diff'] = abs(df_easily['date_diffusion_dt'] - df_easily['date_sortie_dt'])
    df_easily['date_sortie_dt'] = df_easily['date_sortie_dt'].dt.strftime('%d/%m/%Y')

    # Pour chaque fiche_id, trouver l'index de la ligne avec la différence minimale
    idx = df_easily.groupby('fiche_id')['time_diff'].idxmin()

    # Sélectionner ces lignes du dataframe original
    df_easily_keep_only_good_dates = df_easily.loc[idx]



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

    df_lifen["ipp"] = df_lifen["ipp"].astype(int)
    df_lifen["num_sej"] = df_lifen["num_sej"].astype(int)

    df_easily_keep_only_good_dates["ipp"] = df_easily_keep_only_good_dates["ipp"].astype(int)
    df_easily_keep_only_good_dates["num_sej"] = df_easily_keep_only_good_dates["num_sej"].astype(int)

    # On fait d'abord un merge pour avoir accès à date_sortie_easily et date_diffusion_easily
    df_temp = df_lifen.merge(df_easily_keep_only_good_dates[["ipp", "num_sej", "date_sortie_easily", "date_diffusion_easily",
                                        "date_min_val_easily"]], on=["ipp", "num_sej"])


    df_temp['date_envoi_lifen'] = pd.to_datetime(df_temp['date_envoi_lifen'])
    df_temp['date_sortie_easily'] = pd.to_datetime(df_temp['date_sortie_easily'])
    df_temp['date_diffusion_easily'] = pd.to_datetime(df_temp['date_diffusion_easily'], format="%d/%m/%Y")



    # Calculer les différences absolues avec gestion des NaN
    df_temp["diff_date_lifen"] = df_temp.apply(
        lambda row: abs(row["date_envoi_lifen"] - row["date_sortie_easily"]).days
                    if pd.notna(row["date_envoi_lifen"]) and pd.notna(row["date_sortie_easily"])
                    else float('inf'),  # Utiliser l'infini pour les valeurs manquantes
        axis=1
    )

    df_temp["diff_date_easily"] = df_temp.apply(
        lambda row: abs(row["date_diffusion_easily"] - row["date_sortie_easily"]).days
                    if pd.notna(row["date_diffusion_easily"]) and pd.notna(row["date_sortie_easily"])
                    else float('inf'),  # Utiliser l'infini pour les valeurs manquantes
        axis=1
    )


    # Créer une nouvelle colonne pour déterminer quelle source utiliser, avec vérification explicite des NaN
    df_temp["source_optimale"] = "Aucune"

    # Cas où les deux dates sont disponibles et valides
    mask_both_valid = (pd.notna(df_temp["diff_date_lifen"]) & pd.notna(df_temp["diff_date_easily"]) &
                        (df_temp["diff_date_lifen"] != float('inf')) & (df_temp["diff_date_easily"] != float('inf')))

    df_temp.loc[mask_both_valid, "source_optimale"] = df_temp.loc[mask_both_valid].apply(
        lambda row: "Lifen" if row["diff_date_lifen"] <= row["diff_date_easily"] else "Easily",
        axis=1
    )





    # Cas où seule une date est valide
    mask_only_lifen = (pd.notna(df_temp["diff_date_lifen"]) &
                        (df_temp["diff_date_lifen"] != float('inf')) &
                        (~pd.notna(df_temp["diff_date_easily"]) | df_temp["diff_date_easily"] == float('inf')))

    mask_only_easily = (pd.notna(df_temp["diff_date_easily"]) &
                        (df_temp["diff_date_easily"] != float('inf')) &
                        (~pd.notna(df_temp["diff_date_lifen"]) | df_temp["diff_date_lifen"] == float('inf')))

    df_temp.loc[mask_only_lifen, "source_optimale"] = "Lifen"
    df_temp.loc[mask_only_easily, "source_optimale"] = "Easily"

    # Créer la colonne date_diffusion_optimale avec vérification explicite
    df_temp["date_diffusion_optimale"] = df_temp.apply(
        lambda row: row["date_envoi_lifen"] if row["source_optimale"] == "Lifen" and pd.notna(row["date_envoi_lifen"])
                    else row["date_diffusion_easily"] if row["source_optimale"] == "Easily" and pd.notna(row["date_diffusion_easily"])
                    else None,
        axis=1
    )

    # Calculer la différence optimale en jours directement à partir de date_diffusion_optimale
    df_temp["diff_optimale_jours"] = df_temp.apply(
        lambda row: abs((row["date_diffusion_optimale"] - row["date_sortie_easily"]).days )
                    if pd.notna(row["date_diffusion_optimale"]) and pd.notna(row["date_sortie_easily"])
                    else None,
        axis=1
    )

    # Sélectionner pour chaque num_sej la ligne avec la plus petite différence
    df_min = df_temp.sort_values("diff_optimale_jours").groupby("num_sej").first().reset_index()

    # IMPORTANT: Conserver les colonnes source_optimale et date_diffusion_optimale
    columns_to_keep = ["ipp", "num_sej", "date_sortie_lifen", "specialite_lifen",
                        "date_envoi_lifen", "source_optimale", "date_diffusion_optimale", "diff_optimale_jours"]
    df_min = df_min[columns_to_keep]



    # Jointure des données easily - lifen et source optimale
    df_merge = df_min.merge(df_easily_keep_only_good_dates[['ipp','num_sej','date_entree_easily','date_sortie_easily','specialite_easily','date_min_val_easily','date_diffusion_easily']], on=["ipp", "num_sej"])


    # Conversion des colonnes de date
    df_merge["date_sortie_easily"] = pd.to_datetime(df_merge["date_sortie_easily"])
    df_merge["date_diffusion_easily"] = pd.to_datetime(df_merge["date_diffusion_easily"], format="%d/%m/%Y")
    df_merge["date_min_val_easily"] = pd.to_datetime(df_merge["date_min_val_easily"],format='ISO8601')

    # Calcul de la différence entre date de diffusion optimale et date de sortie du patient (en jours)
    df_merge["diff_date_diffusion_sortie"] = df_merge.apply(
        lambda row: (pd.Timestamp(row["date_diffusion_optimale"]).floor('D') -
                    pd.Timestamp(row["date_sortie_easily"]).floor('D')).days
                    if pd.notna(row["date_diffusion_optimale"]) and pd.notna(row["date_sortie_easily"])
                    else None,
        axis=1
    )

    # Calcul de la différence entre date de validation du document et date de sortie du patient (en jours)
    df_merge["diff_validation_easily_sortie_easily"] = (pd.to_datetime(df_merge["date_min_val_easily"].dt.date) -
                                                    pd.to_datetime(df_merge["date_sortie_easily"].dt.date)).dt.days

    # Ajout du calcul pour la 2e statistique : délai d'envoi par rapport à la date de validation du médecin
    df_merge["delai_envoi_validation"] = df_merge.apply(
        lambda row: (pd.Timestamp(row["date_diffusion_optimale"]).floor('D') -
                    pd.Timestamp(row["date_min_val_easily"]).floor('D')).days
                    if pd.notna(row["date_diffusion_optimale"]) and pd.notna(row["date_min_val_easily"])
                    else None,
        axis=1
    )

    # Filtrage pour exclure les lettres validées plus de 3 jours avant la sortie
    df_merge = df_merge[df_merge["diff_validation_easily_sortie_easily"] >= -3]

    # Filtrage pour exclure les lettres validées plus de 3 jours avant la sortie
    df_merge = df_merge[df_merge["diff_validation_easily_sortie_easily"] >= -3]
    df_merge = df_merge[['ipp', 'num_sej', 'source_optimale', 'date_sortie_easily', 'date_envoi_lifen', 'date_diffusion_easily', 'date_min_val_easily','diff_date_diffusion_sortie', 'diff_validation_easily_sortie_easily',
        'delai_envoi_validation']]


    datetime_columns = ['date_sortie_easily', 'date_envoi_lifen', 'date_diffusion_easily','date_min_val_easily']
    df_merge[datetime_columns] = df_merge[datetime_columns].apply(lambda x: x.dt.strftime('%d/%m/%Y'))




    # Affichage des résultats
    st.subheader("Distribution des délais diffusion-sortie (Source optimale)")
    fig = px.histogram(
        df_merge,
        x="diff_date_diffusion_sortie",
        title="Distribution des délais entre diffusion et sortie (Source optimale)",
        nbins=100,
        labels={"diff_date_diffusion_sortie": "Délai (jours)"},
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Répartition des sources optimales
    st.subheader("Répartition des sources optimales")
    source_counts = df_merge["source_optimale"].value_counts()
    fig_sources = px.pie(
        names=source_counts.index,
        values=source_counts.values,
        title="Sources utilisées pour le calcul des délais",
        template="plotly_white"
    )
    st.plotly_chart(fig_sources, use_container_width=True)

    # Statistiques pour le délai global
    st.markdown("#### Statistiques du délai global (diffusion-sortie)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Moyenne", f"{df_merge['diff_date_diffusion_sortie'].mean():.1f} jours")
    col2.metric("Min", f"{df_merge['diff_date_diffusion_sortie'].min()} jours")
    col3.metric("Max", f"{df_merge['diff_date_diffusion_sortie'].max()} jours")
    col4.metric("Médiane", f"{df_merge['diff_date_diffusion_sortie'].median()} jours")

    # 1ère stat : délai d'envoi pour lettres validées le jour de la sortie
    st.subheader("Délai d'envoi pour les lettres validées le jour de la sortie")
    df_validation_jour_sortie = df_merge[df_merge["diff_validation_easily_sortie_easily"] == 0]
    if not df_validation_jour_sortie.empty:
        fig_validation_jour_sortie = px.histogram(
            df_validation_jour_sortie,
            x="diff_date_diffusion_sortie",
            title="Délai d'envoi pour les lettres validées le jour de la sortie",
            nbins=100,
            labels={"diff_date_diffusion_sortie": "Délai (jours)"},
            template="plotly_white",
        )
        st.plotly_chart(fig_validation_jour_sortie, use_container_width=True)

        # Calcul du pourcentage
        pourcentage = (len(df_validation_jour_sortie) / len(df_merge)) * 100
        st.info(f"Nombre de lettres validées le jour de la sortie : {len(df_validation_jour_sortie)} ({pourcentage:.1f}% du total)")

        # Statistiques pour les lettres validées le jour de la sortie
        st.markdown("#### Statistiques du délai pour lettres validées le jour de la sortie")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Moyenne", f"{df_validation_jour_sortie['diff_date_diffusion_sortie'].mean():.1f} jours")
        col2.metric("Min", f"{df_validation_jour_sortie['diff_date_diffusion_sortie'].min()} jours")
        col3.metric("Max", f"{df_validation_jour_sortie['diff_date_diffusion_sortie'].max()} jours")
        col4.metric("Médiane", f"{df_validation_jour_sortie['diff_date_diffusion_sortie'].median()} jours")
    else:
        st.info("Aucune lettre n'a été validée le jour même de la sortie.")

    # 2ème stat : délai d'envoi par rapport à la date de validation du médecin
    st.subheader("Délai d'envoi par rapport à la date de validation")
    fig_delai_validation = px.histogram(
        df_merge,
        x="delai_envoi_validation",
        title="Délai d'envoi par rapport à la date de validation du médecin",
        nbins=100,
        labels={"delai_envoi_validation": "Délai (jours)"},
        template="plotly_white",
    )
    st.plotly_chart(fig_delai_validation, use_container_width=True)

    # Statistiques pour le délai par rapport à la date de validation
    st.markdown("#### Statistiques du délai par rapport à la date de validation")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Moyenne", f"{df_merge['delai_envoi_validation'].mean():.1f} jours")
    col2.metric("Min", f"{df_merge['delai_envoi_validation'].min()} jours")
    col3.metric("Max", f"{df_merge['delai_envoi_validation'].max()} jours")
    col4.metric("Médiane", f"{df_merge['delai_envoi_validation'].median()} jours")

    # Analyse des documents avec délai important
    seuil_ecart = st.slider(
        "Sélectionner un seuil d'écart (en jours)", min_value=0, max_value=100, value=30
    )
    df_large_gap = df_merge[df_merge["diff_date_diffusion_sortie"] > seuil_ecart]
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
