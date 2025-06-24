import base64

import pandas as pd
import plotly.express as px
import streamlit as st


def display_analyse_documents(df_lifen, df_easily):
    st.header("📊 Analyse des délais entre validation, sortie et envoi")

    # Encadré d'introduction avec icône
    st.info("💡 **Objectif** : Évaluer les délais de transmission des lettres de liaison aux patients")

    # Section des indicateurs clés avec colonnes
    st.subheader("🎯 Indicateurs analysés")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **🌐 Délai global**

        Temps entre la sortie patient (Easily) et l'envoi document (Lifen)
        """)

    with col2:
        st.markdown("""
        **📅 Délai J0**

        Focus sur les lettres validées le jour même de la sortie
        """)

    with col3:
        st.markdown("""
        **⏱️ Délai validation**

        Temps entre validation médicale et envoi effectif
        """)

    # Section méthodologie dans un expander
    with st.expander("📋 Méthodologie de la requête", expanded=False):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
            **✅ Règles de calcul :**
            - Délai = date validation ↔ date sortie patient
            - Première version validée prise en compte
            - Dernier séjour pour multi-spécialités
            - Seules les lettres **validées** comptabilisées
            """)

        with col2:
            st.markdown("""
            **⚠️ Limites identifiées :**
            - LL non rattachées au n° de séjour
            - Archivage Lifen depuis le 01/01/2023
            """)

    # Section filtres appliqués
    with st.expander("🔍 Filtres appliqués", expanded=False):
        st.markdown("""
        | Filtre | Critère |
        |--------|---------|
        | **Type de document** | Lettres de liaison (LL) destinées aux patients uniquement |
        | **Validation temporelle** | LL validées > 3 jours avant sortie = exclues |
        | **Unicité par séjour** | 1 seul envoi (le plus proche de la sortie) |
        | **Période d'archivage** | Données Lifen depuis le 01/01/2023 |
        | **Statut validation** | Exclut brouillons, "à corriger", "à valider" |
        """)

    # ====== DÉBUT DES CORRECTIONS ======





    # Vérifications préliminaires
    if df_easily is None or df_easily.empty:
        st.error("❌ Aucune donnée Easily disponible pour l'analyse")
        return

    if df_lifen is None or df_lifen.empty:
        st.error("❌ Aucune donnée Lifen disponible pour l'analyse")
        st.info("💡 Vérifiez que l'API Lifen fonctionne et que les données sont correctement récupérées")
        return

    # Vérifier les colonnes nécessaires
    required_easily_cols = ["pat_IPP", "Num_Venue", "ven_theo", "sej_date_entree",
                           "sej_date_sortie", "CR_Doss_spe", "date_min_val",
                           "LL_J0", "Date diffusion", "fiche_id"]

    missing_cols = [col for col in required_easily_cols if col not in df_easily.columns]
    if missing_cols:
        st.error(f"❌ Colonnes manquantes dans les données Easily: {missing_cols}")
        st.write("Colonnes disponibles:", list(df_easily.columns))
        return

    # ====== TRAITEMENT DES DONNÉES EASILY ======

    df_easily = df_easily[required_easily_cols].copy()

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

    # Vérifier que nous avons encore des données après nettoyage
    if df_easily.empty:
        st.error("❌ Aucune donnée Easily après nettoyage")
        return

    # Convertir les dates avec gestion d'erreurs
    try:
        df_easily['date_sortie_dt'] = pd.to_datetime(df_easily['date_sortie_easily'])
        df_easily['date_diffusion_dt'] = pd.to_datetime(df_easily['date_diffusion_easily'],
                                                       format='%d/%m/%Y', errors='coerce')
    except Exception as e:
        st.error(f"❌ Erreur lors de la conversion des dates: {e}")
        return

    # Calculer la différence avec gestion des NaN
    df_easily['time_diff'] = df_easily.apply(
        lambda row: abs(row['date_diffusion_dt'] - row['date_sortie_dt'])
                   if pd.notna(row['date_diffusion_dt']) and pd.notna(row['date_sortie_dt'])
                   else pd.Timedelta(days=9999),  # Valeur très grande pour les NaN
        axis=1
    )

    df_easily['date_sortie_dt'] = df_easily['date_sortie_dt'].dt.strftime('%d/%m/%Y')

    # CORRECTION PRINCIPALE : Pour chaque fiche_id, trouver l'index avec gestion d'erreurs
    try:
        # Grouper par fiche_id et trouver les indices des différences minimales
        idx_series = df_easily.groupby('fiche_id')['time_diff'].idxmin()

        # Vérifier que tous les indices existent dans le DataFrame
        valid_indices = [idx for idx in idx_series if idx in df_easily.index]
        invalid_indices = [idx for idx in idx_series if idx not in df_easily.index]

        if invalid_indices:
            st.warning(f"⚠️ {len(invalid_indices)} indices invalides détectés et ignorés")

        if not valid_indices:
            st.error("❌ Aucun indice valide trouvé après groupement")
            return

        # Sélectionner uniquement les lignes avec des indices valides
        df_easily_keep_only_good_dates = df_easily.loc[valid_indices].copy()

    except Exception as e:
        st.error(f"❌ Erreur lors du groupement par fiche_id: {e}")
        with st.expander("🔍 Informations de debug"):
            st.write("Shape df_easily:", df_easily.shape)
            st.write("Colonnes:", df_easily.columns.tolist())
            st.write("Types de données:")
            st.write(df_easily.dtypes)
            if 'fiche_id' in df_easily.columns:
                st.write("Valeurs uniques fiche_id:", df_easily['fiche_id'].nunique())
                st.write("Exemples fiche_id:", df_easily['fiche_id'].head(10).tolist())
        return

    # Vérifier que nous avons encore des données
    if df_easily_keep_only_good_dates.empty:
        st.error("❌ Aucune donnée après filtrage par fiche_id")
        return

    # ====== TRAITEMENT DES DONNÉES LIFEN ======

    # Vérifier les colonnes nécessaires pour Lifen
    required_lifen_cols = ["ipp", "num_sej", "date_sortie", "date_envoi", "role_destinataire", "type_sej"]
    missing_lifen_cols = [col for col in required_lifen_cols if col not in df_lifen.columns]

    if missing_lifen_cols:
        st.error(f"❌ Colonnes manquantes dans les données Lifen: {missing_lifen_cols}")
        st.write("Colonnes disponibles:", list(df_lifen.columns))
        return

    # Filtrage et renommage des colonnes pour Lifen
    df_lifen = df_lifen.copy()
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

    df_lifen = df_lifen[["ipp", "num_sej", "date_sortie_lifen", "specialite_lifen",
                        "date_envoi_lifen", "role_destinataire"]]

    # Filtrer les patients uniquement
    df_lifen = df_lifen[df_lifen["role_destinataire"] == "Patient"]

    if df_lifen.empty:
        st.error("❌ Aucune donnée Lifen pour les patients après filtrage")
        return

    # Conversion en entiers avec gestion d'erreurs
    try:
        df_lifen["ipp"] = pd.to_numeric(df_lifen["ipp"], errors='coerce').astype('Int64')
        df_lifen["num_sej"] = pd.to_numeric(df_lifen["num_sej"], errors='coerce').astype('Int64')

        df_easily_keep_only_good_dates["ipp"] = pd.to_numeric(df_easily_keep_only_good_dates["ipp"], errors='coerce').astype('Int64')
        df_easily_keep_only_good_dates["num_sej"] = pd.to_numeric(df_easily_keep_only_good_dates["num_sej"], errors='coerce').astype('Int64')

        # Supprimer les lignes avec des NaN dans les clés de jointure
        df_lifen = df_lifen.dropna(subset=['ipp', 'num_sej'])
        df_easily_keep_only_good_dates = df_easily_keep_only_good_dates.dropna(subset=['ipp', 'num_sej'])

    except Exception as e:
        st.error(f"❌ Erreur lors de la conversion des types: {e}")
        return

    # ====== SUITE DU TRAITEMENT (identique au code original) ======

    # Merge des données
    df_temp = df_lifen.merge(
        df_easily_keep_only_good_dates[["ipp", "num_sej", "date_sortie_easily",
                                       "date_diffusion_easily", "date_min_val_easily"]],
        on=["ipp", "num_sej"],
        how='inner'
    )

    if df_temp.empty:
        st.error("❌ Aucune correspondance trouvée entre les données Easily et Lifen")
        st.info("💡 Vérifiez que les numéros de séjour correspondent entre les deux sources")
        return


    # Conversion des dates
    try:
        df_temp['date_envoi_lifen'] = pd.to_datetime(df_temp['date_envoi_lifen'], errors='coerce')
        df_temp['date_sortie_easily'] = pd.to_datetime(df_temp['date_sortie_easily'], errors='coerce')
        df_temp['date_diffusion_easily'] = pd.to_datetime(df_temp['date_diffusion_easily'],
                                                         format="%d/%m/%Y", errors='coerce')
    except Exception as e:
        st.error(f"❌ Erreur lors de la conversion des dates dans df_temp: {e}")
        return

    # Le reste du code continue exactement comme dans votre version originale...
    # [Ajoutez ici le reste de votre code à partir de la ligne des calculs de différences]

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
    df_merge = df_min.merge(df_easily_keep_only_good_dates[['ipp','num_sej','date_entree_easily','date_sortie_easily',
                                                            'specialite_easily','date_min_val_easily','date_diffusion_easily']], on=["ipp", "num_sej"])

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
    df_merge = df_merge[[
        'ipp',
        'num_sej',
        'source_optimale',
        'date_sortie_easily',
        'date_envoi_lifen',
        'date_diffusion_easily',
        'date_min_val_easily',
        'specialite_easily',  # ← Ajouter cette ligne !
        'diff_date_diffusion_sortie',
        'diff_validation_easily_sortie_easily',
        'delai_envoi_validation'
    ]]

    datetime_columns = ['date_sortie_easily', 'date_envoi_lifen', 'date_diffusion_easily','date_min_val_easily']
    df_merge[datetime_columns] = df_merge[datetime_columns].apply(lambda x: x.dt.strftime('%d/%m/%Y'))

    # Vérification finale
    if df_merge.empty:
        st.error("❌ Aucune donnée finale après tous les traitements")
        return

    # ====== AFFICHAGE DES RÉSULTATS ======

    df_merge = df_merge[df_merge["diff_date_diffusion_sortie"] >= -3]

    # Affichage des résultats
    st.subheader("Distribution des délais diffusion-sortie")
    fig = px.histogram(
        df_merge,
        x="diff_date_diffusion_sortie",
        title="Distribution des délais entre diffusion et sortie",
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
    df_merge = df_merge[df_merge["diff_date_diffusion_sortie"] >= -3]

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



# ====== NOUVEAU : Tableau récapitulatif par service des % de LL validées le jour de la sortie ======

    st.subheader("📊 Tableau récapitulatif par service - % de LL validées le jour de la sortie")

    # Vérifier que nous avons les colonnes nécessaires
    if 'specialite_easily' not in df_merge.columns:
        st.error("❌ Colonne 'specialite_easily' manquante pour l'analyse par service")
    else:
        # Calculer les statistiques par service
        stats_by_service = []

        # Grouper par spécialité
        for service in df_merge['specialite_easily'].unique():
            if pd.isna(service):
                continue

            # Données pour ce service
            df_service = df_merge[df_merge['specialite_easily'] == service]

            # LL validées le jour de la sortie pour ce service
            df_service_j0 = df_service[df_service['diff_validation_easily_sortie_easily'] == 0]

            # Calculs
            total_ll = len(df_service)
            ll_j0 = len(df_service_j0)
            pourcentage_j0 = (ll_j0 / total_ll * 100) if total_ll > 0 else 0

            # Délai moyen pour ce service
            delai_moyen = df_service['diff_date_diffusion_sortie'].mean()
            delai_median = df_service['diff_date_diffusion_sortie'].median()

            # Délai moyen pour les LL validées J0 de ce service
            delai_moyen_j0 = df_service_j0['diff_date_diffusion_sortie'].mean() if ll_j0 > 0 else None
            delai_median_j0 = df_service_j0['diff_date_diffusion_sortie'].median() if ll_j0 > 0 else None

            stats_by_service.append({
                'Service': service,
                'Total LL': total_ll,
                'LL validées J0': ll_j0,
                '% LL validées J0': pourcentage_j0,
                'Délai moyen global (j)': delai_moyen,
                'Délai médian global (j)': delai_median,
                'Délai moyen LL J0 (j)': delai_moyen_j0,
                'Délai médian LL J0 (j)': delai_median_j0
            })

        # Créer le DataFrame des statistiques
        df_stats_services = pd.DataFrame(stats_by_service)

        if not df_stats_services.empty:
            # Trier par pourcentage décroissant
            df_stats_services = df_stats_services.sort_values('% LL validées J0', ascending=False)

            # Formater les colonnes numériques
            df_stats_services['% LL validées J0'] = df_stats_services['% LL validées J0'].round(1)
            df_stats_services['Délai moyen global (j)'] = df_stats_services['Délai moyen global (j)'].round(1)
            df_stats_services['Délai médian global (j)'] = df_stats_services['Délai médian global (j)'].round(1)
            df_stats_services['Délai moyen LL J0 (j)'] = df_stats_services['Délai moyen LL J0 (j)'].round(1)
            df_stats_services['Délai médian LL J0 (j)'] = df_stats_services['Délai médian LL J0 (j)'].round(1)

            # Afficher le tableau avec mise en forme
            st.dataframe(
                df_stats_services,
                use_container_width=True,
                hide_index=True
            )

            # ====== GRAPHIQUES ASSOCIÉS ======

            # 1. Graphique en barres des pourcentages par service
            st.subheader("📈 Pourcentage de LL validées le jour de la sortie par service")

            fig_bar_services = px.bar(
                df_stats_services,  # Top 15 pour la lisibilité
                x='Service',
                y='% LL validées J0',
                title="Pourcentage de LL validées le jour de la sortie par service",
                labels={'% LL validées J0': '% LL validées J0', 'Service': 'Service'},
                template="plotly_white",
                text='% LL validées J0'
            )

            # Personnalisation du graphique
            fig_bar_services.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_bar_services.update_layout(xaxis_tickangle=-45)
            fig_bar_services.update_traces(
                marker_color=['lightgreen' if x >= 50 else 'lightcoral' if x < 25 else 'lightblue'
                             for x in df_stats_services.head(15)['% LL validées J0']]
            )

            st.plotly_chart(fig_bar_services, use_container_width=True)

            # 3. Heatmap des délais par service
            st.subheader("🌡️ Heatmap des délais moyens par service")

            # Préparer les données pour la heatmap
            df_heatmap = df_stats_services[['Service', 'Délai moyen global (j)', 'Délai moyen LL J0 (j)']].copy()
            df_heatmap = df_heatmap.set_index('Service')

            # Créer la heatmap
            fig_heatmap = px.imshow(
                df_heatmap.T,
                title="Délais moyens par service (jours)",
                labels={"x": "Service", "y": "Type de délai", "color": "Délai (jours)"},
                aspect="auto",
                color_continuous_scale="RdYlGn_r"  # Rouge = délai élevé, Vert = délai faible
            )

            fig_heatmap.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_heatmap, use_container_width=True)

            # ====== STATISTIQUES GLOBALES ======

            st.subheader("📋 Statistiques globales par service")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                meilleur_service = df_stats_services.iloc[0]['Service']
                meilleur_pourcentage = df_stats_services.iloc[0]['% LL validées J0']
                st.metric(
                    "🥇 Meilleur service",
                    f"{meilleur_pourcentage:.1f}%",
                    delta=f"{meilleur_service}"
                )

            with col2:
                pire_service = df_stats_services.iloc[-1]['Service']
                pire_pourcentage = df_stats_services.iloc[-1]['% LL validées J0']
                st.metric(
                    "📉 Service à améliorer",
                    f"{pire_pourcentage:.1f}%",
                    delta=f"{pire_service}"
                )

            with col3:
                moyenne_globale = df_stats_services['% LL validées J0'].mean()
                st.metric(
                    "📊 Moyenne générale",
                    f"{moyenne_globale:.1f}%"
                )

            with col4:
                services_objectif = len(df_stats_services[df_stats_services['% LL validées J0'] >= 50])
                total_services = len(df_stats_services)
                st.metric(
                    "🎯 Services ≥ 50%",
                    f"{services_objectif}/{total_services}",
                    delta=f"{(services_objectif/total_services*100):.1f}%"
                )

            # ====== ANALYSE DES SERVICES À RISQUE ======

            with st.expander("⚠️ Analyse des services à améliorer"):
                services_faibles = df_stats_services[df_stats_services['% LL validées J0'] < 25]

                if not services_faibles.empty:
                    st.markdown("**Services avec moins de 25% de LL validées le jour de la sortie :**")
                    for _, service in services_faibles.iterrows():
                        st.markdown(f"- **{service['Service']}** : {service['% LL validées J0']:.1f}% "
                                  f"({service['LL validées J0']}/{service['Total LL']} LL)")
                else:
                    st.success("✅ Aucun service en dessous de 25% de LL validées J0")

# 2ème stat : délai d'envoi par rapport à la date de validation du médecin
    # EXCLUSION DES LL VALIDÉES LE WEEKEND

    # Convertir date_min_val_easily en datetime si ce n'est pas déjà fait
    df_merge['date_min_val_easily_dt'] = pd.to_datetime(df_merge['date_min_val_easily'], dayfirst=True)

    # Ajouter une colonne pour identifier le jour de la semaine (0=Lundi, 6=Dimanche)
    df_merge['jour_semaine_validation'] = df_merge['date_min_val_easily_dt'].dt.dayofweek

    # Filtrer pour exclure les validations du weekend (samedi=5, dimanche=6)
    df_merge_sans_weekend = df_merge[~df_merge['jour_semaine_validation'].isin([5, 6])].copy()

    # Afficher les informations de filtrage
    len(df_merge)
    nb_weekend = len(df_merge[df_merge['jour_semaine_validation'].isin([5, 6])])
    nb_sans_weekend = len(df_merge_sans_weekend)


    if df_merge_sans_weekend.empty:
        st.warning("⚠️ Aucune donnée après exclusion des validations weekend")
        return

    st.subheader("Délai d'envoi à J0 de la date de validation (hors weekend)")
    st.info(f"📊 **{nb_sans_weekend} hors weekend "
         f"({nb_weekend} validations weekend exclues)")

    df_merge_sans_weekend = df_merge_sans_weekend[df_merge_sans_weekend["delai_envoi_validation"] >= -3]


    fig_delai_validation = px.histogram(
        df_merge_sans_weekend,
        x="delai_envoi_validation",
        title="Délai d'envoi par rapport à la date de validation du médecin (hors validations weekend)",
        nbins=100,
        labels={"delai_envoi_validation": "Délai (jours)"},
        template="plotly_white",
    )
    st.plotly_chart(fig_delai_validation, use_container_width=True)

    # Optionnel : Afficher la répartition par jour de la semaine
    with st.expander("📅 Répartition des validations par jour de la semaine"):
        jours_semaine = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
        df_merge['nom_jour_validation'] = df_merge['jour_semaine_validation'].map(jours_semaine)

        repartition_jours = df_merge['nom_jour_validation'].value_counts().reindex(jours_semaine.values())

        fig_jours = px.bar(
            x=repartition_jours.index,
            y=repartition_jours.values,
            title="Nombre de validations par jour de la semaine",
            labels={"x": "Jour de la semaine", "y": "Nombre de validations"},
            template="plotly_white"
        )
        # Colorer les weekends en rouge
        colors = ['lightblue' if jour not in ['Samedi', 'Dimanche'] else 'lightcoral' for jour in
                  repartition_jours.index]
        fig_jours.update_traces(marker_color=colors)
        st.plotly_chart(fig_jours, use_container_width=True)

    # Statistiques pour le délai par rapport à la date de validation (hors weekend)
    st.markdown("#### Statistiques du délai d'envoi à J0 de la date de validation (hors weekend)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Moyenne", f"{df_merge_sans_weekend['delai_envoi_validation'].mean():.1f} jours")
    col2.metric("Min", f"{df_merge_sans_weekend['delai_envoi_validation'].min()} jours")
    col3.metric("Max", f"{df_merge_sans_weekend['delai_envoi_validation'].max()} jours")
    col4.metric("Médiane", f"{df_merge_sans_weekend['delai_envoi_validation'].median()} jours")


    # Analyse des documents avec délai important
    seuil_ecart = st.slider(
        "Sélectionner un seuil d'écart (en jours)", min_value=0, max_value=100, value=30, key="slider_grand_delai"
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
