import base64

import pandas as pd
import streamlit as st


def create_download_link(df, filename):
    """Crée un lien de téléchargement pour un DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="highlight">Télécharger {filename}</a>'
    return href

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
