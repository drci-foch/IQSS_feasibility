import asyncio
import logging
import math
import os
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Annotated

import oracledb
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
import sys
sys.path.append(os.path.abspath('..'))  # Chemin vers le dossier contenant auth.py
from auth import get_current_user

# Configure logging avec niveau réduit pour éviter le spam
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("lifen_api.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Réduire les logs uvicorn
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application FastAPI
app = FastAPI(
    title="API Lifen",
    description="API pour récupérer les données de diffusion Lifen depuis Oracle",
    version="1.0.0",
)

# Configuration CORS plus restrictive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Modèle de données pour la réponse Lifen
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
        from_attributes = True

# Classes pour la gestion des longues périodes avec seuils réduits
class PeriodStrategy:
    """Calcule la stratégie optimale selon la durée de la période"""

    @staticmethod
    def calculate_optimal_strategy(start_date: str, end_date: str) -> tuple[int, int, str]:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        duration = (end - start).days

        # Seuils réduits pour éviter les timeouts
        if duration <= 15:
            return 1, duration, "direct"
        elif duration <= 45:
            return math.ceil(duration / 15), 15, "medium_chunks"
        elif duration <= 120:
            return math.ceil(duration / 10), 10, "small_chunks"
        else:
            return math.ceil(duration / 7), 7, "micro_chunks"

    @staticmethod
    def split_period_intelligently(start_date: str, end_date: str) -> list[tuple[str, str]]:
        num_chunks, chunk_size, strategy = PeriodStrategy.calculate_optimal_strategy(start_date, end_date)

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        chunks = []
        current = start

        while current < end:
            chunk_end = min(current + timedelta(days=chunk_size), end)
            chunks.append((
                current.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            ))
            current = chunk_end + timedelta(days=1)

        return chunks

# Middleware de timeout plus strict
class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: int = 60):  # Réduit à 60 secondes
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except TimeoutError:
            logger.error(f"⏰ Timeout {self.timeout}s pour {request.url.path}")
            raise HTTPException(status_code=504, detail=f"Requête timeout après {self.timeout}s")

# Middleware de logging des requêtes
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(f"START {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(f"SUCCESS {request.method} {request.url.path} - {duration:.2f}s")
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"ERROR {request.method} {request.url.path} - {duration:.2f}s - {str(e)}")
            raise

# Ajout des middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TimeoutMiddleware, timeout=60)

# Context manager pour les connexions Oracle robuste
@contextmanager
def get_oracle_connection_context():
    """Context manager robuste pour les connexions Oracle"""
    connection = None
    try:
        oracle_user = os.getenv("ORACLE_USER")
        oracle_password = os.getenv("ORACLE_PASSWORD")
        oracle_dsn = os.getenv("ORACLE_DSN")

        if not all([oracle_user, oracle_password, oracle_dsn]):
            raise ValueError("Variables d'environnement Oracle manquantes")

        # Connexion simple SANS configuration de session
        connection = oracledb.connect(
            user=oracle_user,
            password=oracle_password,
            dsn=oracle_dsn
        )

        # Configuration de session minimale (seulement ce qui est supporté)
        try:
            cursor = connection.cursor()
            # Seulement le format de date (généralement supporté)
            cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD'")
            cursor.close()
        except Exception as e:
            # Si même ça échoue, on continue sans configuration
            logger.warning(f"Impossible de configurer la session Oracle: {str(e)}")

        yield connection

    except Exception as e:
        logger.error(f"ERREUR connexion Oracle: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de connexion à la base de données: {str(e)}"
        )
    finally:
        if connection:
            try:
                connection.close()
                logger.debug("Connexion Oracle fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture Oracle: {str(e)}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Fonction ultra-robuste pour l'API Easily

def get_venue_numbers_from_easily(start_date: str, end_date: str, max_retries: int = 2):
    """Version ultra-robuste avec timeout court"""

    for attempt in range(max_retries):
        session = None
        try:
            easily_api_url = "http://localhost:8000/api/patients/comptes-rendus"
            params = {"start_date": start_date, "end_date": end_date}

            timeout = 25  # 25 secondes max

            logger.info(f"API Easily tentative {attempt + 1}/{max_retries}")

            # Session avec configuration agressive
            session = requests.Session()
            session.headers.update({
                'Connection': 'close',
                'Accept': 'application/json',
                'User-Agent': 'Lifen-API/1.0',
                'Keep-Alive': 'timeout=5, max=1'
            })

            response = session.get(
                easily_api_url,
                params=params,
                timeout=timeout,
                stream=False
            )

            if response.status_code != 200:
                logger.error(f"API Easily: HTTP {response.status_code}")
                response.close()

                if attempt < max_retries - 1:
                    wait_time = 1 + attempt
                    logger.warning(f"Retry dans {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"API Easily échec: HTTP {response.status_code}"
                    )

            try:
                data = response.json()
                response.close()
            except Exception as e:
                response.close()
                raise ValueError(f"Réponse JSON invalide: {str(e)}")

            logger.info(f"API Easily: {len(data)} enregistrements")

            # Extraction optimisée des venues
            venue_numbers = set()

            for item in data:
                if not isinstance(item, dict) or "Num_Venue" not in item:
                    continue

                venue_value = item["Num_Venue"]

                if venue_value is None or venue_value == "":
                    continue

                if isinstance(venue_value, float) and math.isnan(venue_value):
                    continue

                if isinstance(venue_value, str) and venue_value.lower() in ['nan', 'null', '', 'none']:
                    continue

                try:
                    venue_int = int(float(venue_value))
                    if venue_int > 0:
                        venue_numbers.add(venue_int)
                except (ValueError, TypeError, OverflowError):
                    continue

            venue_list = sorted(venue_numbers)
            logger.info(f"{len(venue_list)} venues valides extraites")

            return venue_list

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout tentative {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise HTTPException(
                    status_code=504,
                    detail=f"Timeout API Easily après {max_retries} tentatives"
                )

        except requests.exceptions.ConnectionError:
            logger.error(f"Connexion échouée tentative {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Impossible de contacter l'API Easily"
                )

        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur lors de la récupération des venues: {str(e)}"
                )
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

def execute_query_in_batches(conn, venues_list, start_date=None, end_date=None, batch_size=150):
    """Version optimisée avec batches très petits SANS timeout Oracle"""
    if not venues_list:
        logger.warning("Liste de venues vide")
        return []

    results = []
    total_batches = (len(venues_list) - 1) // batch_size + 1

    logger.info(f"Traitement {len(venues_list)} venues en {total_batches} lots de {batch_size}")

    for i in range(0, len(venues_list), batch_size):
        batch_num = i // batch_size + 1
        batch = venues_list[i:i + batch_size]

        cursor = None
        try:
            # Validation du batch
            valid_batch = [int(venue) for venue in batch if isinstance(venue, int | str) and str(venue).isdigit() and int(venue) > 0]

            if not valid_batch:
                logger.warning(f"Lot {batch_num}: aucune venue valide")
                continue

            # Requête simplifiée avec limite stricte
            in_clause = ", ".join([str(venue) for venue in valid_batch])

            query = f"""
            SELECT *
            FROM NEUSTE.DOCUMENTS
            WHERE NUM_SEJ IN ({in_clause})
                AND TYPE_DOC = 'Lettre de liaison'
                AND ROWNUM <= 3000
            ORDER BY DATE_ENVOI DESC
            """

            logger.info(f"Lot {batch_num}/{total_batches}: {len(valid_batch)} venues")

            cursor = conn.cursor()
            # PAS de configuration de timeout Oracle
            cursor.execute(query)

            # Récupération avec limite
            rows = cursor.fetchall()

            if rows:
                columns = [col[0].lower() for col in cursor.description]

                batch_results = [
                    {columns[j]: row[j] for j in range(len(columns))}
                    for row in rows
                ]

                results.extend(batch_results)
                logger.info(f"Lot {batch_num}: {len(batch_results)} documents")
            else:
                logger.info(f"Lot {batch_num}: aucun résultat")

        except Exception as e:
            logger.error(f"Erreur lot {batch_num}: {str(e)}")
            continue

        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass

    logger.info(f"Total: {len(results)} documents trouvés")
    return results

# Fonction simplifiée pour les longues périodes
def process_long_period_by_chunks(start_date: str, end_date: str, use_easily_api: bool = True) -> list[LifenRecord]:
    """Version simplifiée et plus robuste"""

    chunks = PeriodStrategy.split_period_intelligently(start_date, end_date)
    num_chunks, chunk_size, strategy = PeriodStrategy.calculate_optimal_strategy(start_date, end_date)

    logger.info(f"📅 Stratégie {strategy}: {len(chunks)} chunks")

    all_results = []
    successful_chunks = 0

    for i, (chunk_start, chunk_end) in enumerate(chunks):
        logger.info(f"🔄 Chunk {i+1}/{len(chunks)}: {chunk_start} → {chunk_end}")

        try:
            # Délai court entre chunks
            if i > 0:
                time.sleep(0.5)

            # Récupération des venues
            chunk_venues = get_venue_numbers_from_easily(chunk_start, chunk_end, max_retries=2)

            if chunk_venues:
                with get_oracle_connection_context() as conn:
                    chunk_results = execute_query_in_batches(conn, chunk_venues)

                all_results.extend(chunk_results)
                successful_chunks += 1
                logger.info(f"✅ Chunk {i+1}: {len(chunk_results)} documents")
            else:
                logger.info(f"ℹ️ Chunk {i+1}: aucune venue")
                successful_chunks += 1

        except Exception as e:
            logger.error(f"❌ Chunk {i+1} échoué: {str(e)}")
            continue

    logger.info(f"🏁 Terminé: {successful_chunks}/{len(chunks)} chunks, {len(all_results)} documents")

    # Déduplication rapide
    if all_results:
        seen = set()
        deduplicated = []

        for result in all_results:
            key = result.get('id_doc_lifen') or f"{result.get('num_sej')}_{result.get('date_envoi')}"
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)

        logger.info(f"🔄 Après déduplication: {len(deduplicated)} documents uniques")
        all_results = deduplicated

    return [LifenRecord(**record) for record in all_results]

# Route principale ultra-robuste

@app.get("/api/lifen/data", response_model=list[LifenRecord])
async def get_lifen_data(
    num_venues: Annotated[str | None, Query(description="Numéros de venue séparés par des virgules")] = None,
    start_date: Annotated[str | None, Query(description="Date début (YYYY-MM-DD)")] = None,
    end_date: Annotated[str | None, Query(description="Date fin (YYYY-MM-DD)")] = None,
    use_easily_api: Annotated[bool, Query(description="Utiliser l'API Easily")] = True,
    current_user: str = Depends(get_current_user)
):
    start_time = time.time()
    request_id = f"{int(time.time())}"

    logger.info(f"Requête {request_id} démarrée")

    try:
        # Validation stricte
        if not num_venues and not (start_date and end_date):
            raise HTTPException(
                status_code=400,
                detail="Paramètres manquants: num_venues OU (start_date ET end_date)"
            )

        # Validation des dates avec limite plus stricte
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')

                if start_dt > end_dt:
                    raise HTTPException(400, "start_date > end_date")

                duration = (end_dt - start_dt).days
                if duration > 365:  # Limite très stricte
                    raise HTTPException(400, f"Période trop longue: {duration} jours (max 120)")

            except ValueError:
                raise HTTPException(400, "Format de date invalide (YYYY-MM-DD)")

        # Traitement des venues spécifiées
        if num_venues:
            logger.info("Mode venues spécifiées")
            venues_list = []

            for v in num_venues.split(","):
                try:
                    venue_num = int(v.strip())
                    if venue_num > 0:
                        venues_list.append(venue_num)
                except (ValueError, TypeError):
                    logger.warning(f"Venue invalide: {v.strip()}")

            if not venues_list:
                raise HTTPException(400, "Aucune venue valide")

            venues_list = sorted(set(venues_list))
            logger.info(f"Recherche {len(venues_list)} venues")

            with get_oracle_connection_context() as conn:
                batch_results = execute_query_in_batches(conn, venues_list)

            results = [LifenRecord(**record) for record in batch_results]

        # Traitement par dates
        elif start_date and end_date and use_easily_api:
            duration = (datetime.strptime(end_date, '%Y-%m-%d') -
                       datetime.strptime(start_date, '%Y-%m-%d')).days

            logger.info(f"Mode dates: {duration} jours")

            if duration <= 20:  # Seuil très bas
                logger.info("Traitement direct")
                venues_list = get_venue_numbers_from_easily(start_date, end_date)

                if not venues_list:
                    return []

                with get_oracle_connection_context() as conn:
                    batch_results = execute_query_in_batches(conn, venues_list)

                results = [LifenRecord(**record) for record in batch_results]
            else:
                logger.info("Traitement par chunks")
                results = process_long_period_by_chunks(start_date, end_date, use_easily_api)

        else:
            raise HTTPException(400, "Configuration invalide")

        # Statistiques finales
        elapsed = time.time() - start_time
        logger.info(f"Requête {request_id} terminée: {len(results)} résultats en {elapsed:.2f}s")

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur critique requête {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erreur interne: {str(e)}")


# Route de santé
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Route métadonnées avec limites plus strictes
@app.get("/api/lifen/metadata")
def get_period_metadata(
    start_date: Annotated[str, Query(description="Date début (YYYY-MM-DD)")] = ...,
    end_date: Annotated[str, Query(description="Date fin (YYYY-MM-DD)")] = ...,
    current_user: str = Depends(get_current_user)
):
    try:
        duration = (datetime.strptime(end_date, '%Y-%m-%d') -
                   datetime.strptime(start_date, '%Y-%m-%d')).days

        num_chunks, chunk_size, strategy = PeriodStrategy.calculate_optimal_strategy(start_date, end_date)
        chunks = PeriodStrategy.split_period_intelligently(start_date, end_date)

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "duration_days": duration
            },
            "strategy": {
                "type": strategy,
                "num_chunks": num_chunks,
                "chunk_size_days": chunk_size,
                "estimated_time_seconds": duration * 0.3
            },
            "chunks": [{"start": start, "end": end} for start, end in chunks]
        }
    except Exception as e:
        raise HTTPException(400, f"Format de date invalide: {str(e)}")


# Point d'entrée avec configuration uvicorn optimisée
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="error",  # Minimal logging
        access_log=False,
        timeout_keep_alive=10,
        timeout_graceful_shutdown=5,
        limit_concurrency=50,
        limit_max_requests=1000
    )
