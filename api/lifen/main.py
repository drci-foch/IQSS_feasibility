import logging
import os
from datetime import date

import oracledb
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application FastAPI
app = FastAPI(
    title="API Lifen",
    description="API pour récupérer les données de diffusion Lifen depuis Oracle",
    version="1.0.0",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèle de données pour la réponse Lifen basé sur la structure réelle de la table


class LifenRecord(BaseModel):
    # Champs existants
    id_doc_lifen: str | None = None
    service: str | None = None
    type_doc: str | None = None
    nom_destinataire: str | None = None
    num_sej: int | None = None
    statut_doc: str | None = None
    canal_envoi: str | None = None
    role_destinataire: str | None = None
    date_envoi: date | None = None
    statut_envoi: str | None = None
    id_destinataire: str | None = None

    # Nouveaux champs ajoutés selon la structure de table
    date_creation_doc: date | None = None
    rapprochement_patient_gam: str | None = None
    ipp: str | None = None
    type_sej: str | None = None
    uf: str | None = None
    date_admission: date | None = None
    date_sortie: date | None = None
    ins_statut: str | None = None
    dmp_statut: str | None = None
    code_loinc: str | None = None
    possede_mail_mss: str | None = None
    possede_mail_apicrypt: str | None = None
    envoye_avec_cda: str | None = None
    raison_non_envoi: str | None = None
    id_etablissement: str | None = None
    finess: str | None = None
    id_etablissement_lifen: str | None = None
    id_sej_lifen: str | None = None
    periode: int | None = None

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2


# Connexion à la base de données Oracle
def get_oracle_connection():
    try:
        # Récupérer les informations de connexion depuis les variables d'environnement
        oracle_user = os.getenv("ORACLE_USER")
        oracle_password = os.getenv("ORACLE_PASSWORD")
        oracle_dsn = os.getenv("ORACLE_DSN")  # Format: host:port/service_name

        # Établir la connexion
        connection = oracledb.connect(user=oracle_user, password=oracle_password, dsn=oracle_dsn)

        return connection
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de connexion à la base de données Oracle: {str(e)}",
        )


# Fonction pour récupérer les numéros de venue depuis l'API Easily
def get_venue_numbers_from_easily(start_date: str, end_date: str):
    try:
        # URL de l'API Easily (à adapter selon votre configuration)
        easily_api_url = "http://localhost:8000/api/patients/comptes-rendus"

        # Paramètres de la requête
        params = {"start_date": start_date, "end_date": end_date}

        # Effectuer la requête à l'API Easily
        response = requests.get(easily_api_url, params=params)

        # Vérifier si la requête a réussi
        if response.status_code != 200:
            logger.error(f"Erreur lors de la requête à l'API Easily: {response.status_code}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de la récupération des données depuis l'API Easily: {response.status_code}",
            )

        # Récupérer les données de la réponse
        data = response.json()

        # Extraire les numéros de venue
        venue_numbers = []
        for item in data:
            if "Num_Venue" in item and item["Num_Venue"]:
                try:
                    venue_numbers.append(int(item["Num_Venue"]))  # Convert to integer
                except (ValueError, TypeError):
                    logger.warning(f"Skipping invalid venue number: {item['Num_Venue']}")

        logger.info(f"Récupération de {len(venue_numbers)} numéros de venue depuis l'API Easily")
        return venue_numbers

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des numéros de venue: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des numéros de venue: {str(e)}",
        )


# Fonction pour exécuter la requête par lots
def execute_query_in_batches(conn, venues_list, start_date=None, end_date=None, batch_size=500):
    results = []

    # Traitement des venues par lots pour éviter la limite d'Oracle sur les paramètres
    for i in range(0, len(venues_list), batch_size):
        batch = venues_list[i : i + batch_size]

        # Construire la condition IN directement avec les valeurs entières
        in_clause = ", ".join([str(venue) for venue in batch])
        logger.info(
            f"Traitement du lot {i // batch_size + 1}/{(len(venues_list) - 1) // batch_size + 1}, taille: {len(batch)}"
        )
        logger.info(f"Clause IN pour ce lot: {in_clause}")

        # Construire la requête SQL
        query = f"""
        SELECT *
        FROM 
            NEUSTE.DOCUMENTS  
        WHERE 
            NUM_SEJ IN ({in_clause})
            AND TYPE_DOC = 'Lettre de liaison'
        """

        try:
            # Exécuter la requête
            cursor = conn.cursor()
            logger.info(f"Executing query: {query}")
            cursor.execute(query)

            # Récupérer les résultats
            rows = cursor.fetchall()
            columns = [column[0].lower() for column in cursor.description]

            # Convertir les résultats en dictionnaires
            for row in rows:
                result_dict = {columns[i]: row[i] for i in range(len(columns))}
                results.append(result_dict)

            cursor.close()
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du lot {i // batch_size + 1}: {str(e)}")
            raise e

    return results


# Route pour récupérer les données Lifen par dates
@app.get("/api/lifen/data", response_model=list[LifenRecord])
def get_lifen_data(
    num_venues: str | None = Query(
        None,
        description="List of venue numbers separated by commas (optional)",
    ),
    start_date: str | None = Query(None, description="Start date (format YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (format YYYY-MM-DD)"),
    use_easily_api: bool = Query(True, description="Whether to use Easily API for venue numbers when dates are provided"),
):
    try:
        venues_list = []

        # If num_venues is provided, use these numbers
        if num_venues:
            venues_list = []
            for v in num_venues.split(","):
                try:
                    venues_list.append(int(v.strip()))  # Convert to integer
                except (ValueError, TypeError):
                    logger.warning(f"Skipping invalid venue number: {v.strip()}")
            venues_list = list(set(venues_list))
            logger.info(f"Searching for {len(venues_list)} specified venues")
        # Otherwise, if dates are provided AND use_easily_api is True, get venue numbers from Easily API
        elif start_date and end_date and use_easily_api:
            venues_list = get_venue_numbers_from_easily(start_date, end_date)
            logger.info(f"Retrieved {len(venues_list)} venues from Easily API")
        # If dates are provided but use_easily_api is False, return an error
        elif start_date and end_date:
            logger.warning("Date range provided but use_easily_api is False")
            raise HTTPException(
                status_code=400,
                detail="Cannot use date range without Easily API. Please provide venue numbers directly.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="You must provide either 'num_venues', or 'start_date' AND 'end_date' with use_easily_api=True",
            )

        # Check if we have venue numbers to search for
        if not venues_list:
            logger.warning("No venue numbers found for search")
            return []

        # Obtenir une connexion à la base de données Oracle
        conn = get_oracle_connection()

        # Exécuter la requête par lots
        batch_results = execute_query_in_batches(conn, venues_list, start_date, end_date)

        # Fermer la connexion
        conn.close()

        # Convertir les résultats en objets LifenRecord
        results = [LifenRecord(**record) for record in batch_results]

        logger.info(f"Requête réussie. {len(results)} enregistrements trouvés.")
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des données: {str(e)}",
        )


# Point d'entrée principal
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
