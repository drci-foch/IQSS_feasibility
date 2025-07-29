
import logging
import os
from datetime import datetime
from typing import Annotated

import pyodbc
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Configuration logging plus légère
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application FastAPI
app = FastAPI(
    title="API de Requêtes Médicales",
    description="API pour interroger la base de données des comptes rendus patients",
    version="1.0.0",
)

# Configuration CORS plus restrictive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Modèle de données pour la réponse (identique)
class PatientRecord(BaseModel):
    annee: int
    mois: str
    ll_j0: int = Field(alias="LL_J0")
    nuit_1: int
    pat_ipp: str = Field(alias="pat_IPP")
    pat_date_deces: datetime | None = None
    ven_id: int
    fiche_id: int
    sej_date_entree: datetime
    sej_uf_medicale_code: str
    sej_date_der_entree: datetime
    sej_date_sortie: datetime
    uf_der_pass: str
    cr_der_sej: str
    num_venue: int = Field(alias="Num_Venue")
    ven_theo: int
    cr_courrier: str | None = Field(alias="CR_courrier", default="")
    type_courrier: str | None = Field(alias="Type_courrier", default="")
    dos_spe_esl: str | None = Field(alias="Dos_Spe_ESL", default="")
    cr_doss_spe: str | None = Field(alias="CR_Doss_spe", default="")
    fic_date_creation: datetime
    fic_date_modification: datetime | None = None
    date_min_val: datetime
    date_diffusion: str | None = Field(alias="Date diffusion", default=None)
    statut_envoi: str | None = Field(alias="Statut Envoi", default=None)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    @validator("*", pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

# Configuration de la connexion à la base de données avec timeout
def get_db_connection():
    try:
        connection_string = os.getenv(
            "DB_CONNECTION_STRING",
            "DRIVER={SQL Server};SERVER=your_server;DATABASE=your_db;UID=your_username;PWD=your_password;TrustServerCertificate=yes"",
        )
        # Ajouter timeout de connexion
        conn = pyodbc.connect(connection_string, timeout=15)
        return conn
    except Exception as e:
        logger.error(f"Erreur connexion DB: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de connexion à la base de données: {str(e)}",
        ) from None

# Route de santé pour Easily
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "easily",
        "timestamp": datetime.now().isoformat()
    }

# Fonction pour nettoyer les résultats de la requête (identique)
def clean_query_results(rows, columns):
    results = []
    for row in rows:
        result_dict = {}
        for i, col in enumerate(columns):
            if row[i] is None:
                result_dict[col] = None
            else:
                result_dict[col] = row[i]
        results.append(result_dict)
    return results


def execute_query(conn, start_date=None, end_date=None, venues=None):
    cursor = conn.cursor()

    # Timeout au niveau du curseur
    cursor.execute("SET LOCK_TIMEOUT 15000")

    include_second_part = True
    date_condition = ""
    venue_condition = ""

    if venues and venues.strip():
        venue_condition = f"""
        CASE
            WHEN f.fic_venue IS NULL THEN 0
            WHEN f.fic_venue IS NOT NULL THEN v.ven_numero
        END IN ({venues})"""
        include_second_part = False
    else:
        if start_date and end_date:
            date_condition = f"s2.sej_date_sortie BETWEEN '{start_date}' AND '{end_date}'"
        else:
            date_condition = "YEAR(s2.sej_date_sortie) = YEAR(GETDATE())"

    # SYNTAXE CORRIGÉE : DISTINCT TOP au lieu de TOP DISTINCT
    sql_query_part1 = f"""
DECLARE @startOfCurrentMonth DATETIME
SET @startOfCurrentMonth = DATEADD(YEAR, DATEDIFF(year, 0, CURRENT_TIMESTAMP), 0)

/*recherche fiche avec venue*/
SELECT DISTINCT TOP 5000
    year(s2.sej_date_sortie) AS annee,
    DateName(Month,s2.sej_date_sortie) AS mois,
    datediff(day,s2.sej_date_sortie,date_min_val) AS LL_J0,
    CASE
        WHEN s1.sej_date_entree >= ven_admission THEN datediff(day,s1.sej_date_entree,s2.sej_date_sortie)
        WHEN s1.sej_date_entree < ven_admission THEN datediff(day,ven_admission,s2.sej_date_sortie)
    END AS nuit_1,
    p.pat_ipp AS pat_IPP,
    p.pat_date_deces,
    v.ven_id,
    f.fiche_id,
    s1.sej_date_entree,
    s1.sej_uf_medicale_code,
    s3.date_der AS sej_date_der_entree,
    s2.sej_date_sortie AS sej_date_sortie,
    s2.sej_uf_medicale_code AS uf_der_pass,
    cr.cr_libelle_long AS cr_der_sej,
    CASE
        WHEN f.fic_venue IS NULL THEN 0
        WHEN f.fic_venue IS NOT NULL THEN v.ven_numero
    END AS Num_Venue,
    v.ven_numero AS ven_theo,
    cr3.cr_libelle_long AS CR_courrier,
    dfs.fos_libelle AS Type_courrier,
    ds.dos_libelle_court AS Dos_Spe_ESL,
    CASE
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Vasculaire Foch' THEN 'VASCULAIRE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Urologique Foch' THEN 'UROLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Réa Foch' THEN 'REANIMATION'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison ORL Foch' THEN 'ORL'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Oncologie Foch' THEN 'ONCOLOGIE'
        WHEN dfs.fos_libelle ='CR HDJ Oncologie Foch' THEN 'ONCOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Digestive Foch' THEN 'DIGESTIF'
        WHEN dfs.fos_libelle ='CR HDJ Endoscopie Digestive Foch' THEN 'ENDODIG'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Cardiologie Foch' THEN 'CARDIOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Unité Vanderbilt Foch ' THEN 'VANDERBILDT'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison UPHU Foch ' THEN 'UPHU'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Throm Foch' THEN 'NEUROLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Throm SG Foch' THEN 'NEUROLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Foch DOG' THEN 'OBSTETRIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Pédiatrie Foch' THEN 'NEONATOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Gynécologie Foch' THEN 'GYNECOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Thoracique Foch' THEN 'THORACIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Thoracique Foch' AND ds.dos_libelle_court = 'Chirurgie Thoracique Foch' THEN 'THORACIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison USIR Foch ' AND ds.dos_libelle_court = 'Chirurgie Thoracique Foch' THEN 'THORACIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Gériatrie Foch' THEN 'GERIATRIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison M.P.R Foch' THEN 'MPR'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison SSPI Foch' THEN 'ANESTHESIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Médecine interne et Polyvalente Foch' THEN 'MEDECINE INTERNE ET POLYVALENTE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Diabétologie Foch ' THEN 'MEDECINE INTERNE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison NRDT Foch' THEN 'NEUROCHIRURGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Neurochirurgie Foch' THEN 'NEUROCHIRURGIE'
        WHEN dfs.fos_libelle ='CR Urgences' THEN 'URGENCES'
        ELSE cr4.cr_libelle_long
    END AS CR_Doss_spe,
    f.fic_date_creation,
    f.fic_date_modification,
    fhs2.date_min_val,
    convert(Varchar, EDES.dest_diffusion_date, 103) as 'Date diffusion',
    CASE EDES.st_id
        WHEN 1 THEN 'A diffuser'
        WHEN 3 THEN 'Echec'
        WHEN 4 THEN 'Diffuse'
        WHEN 7 THEN 'Annule'
        ELSE 'Pas dans boite envoi'
    END as 'Statut Envoi'
FROM
    NOYAU.patient.VENUE v
    LEFT JOIN NOYAU.patient.SEJOUR s1 ON s1.ven_id = v.ven_id
        AND v.ven_supprime != 1
        AND s1.sej_numero = '1'
        AND ven_type IN (1,8)
    LEFT JOIN NOYAU.patient.SEJOUR s2 ON s2.ven_id = v.ven_id
        AND v.ven_supprime != 1
        AND s2.sej_est_dernier_sejour = 1
    LEFT JOIN (
        SELECT s.ven_id, MIN(s.sej_date_entree) AS date_der, s.sej_uf_medicale_code
        FROM NOYAU.patient.SEJOUR s
        INNER JOIN noyau.patient.sejour s2 ON s.sej_uf_medicale_code = s2.sej_uf_medicale_code
            AND s.ven_id = s2.ven_id
            AND s2.sej_est_dernier_sejour = 1
        WHERE s2.sej_est_dernier_sejour = 1 AND s.ven_id = s2.ven_id
        GROUP BY s.ven_id, s.sej_uf_medicale_code
    ) AS s3 ON s3.ven_id = s2.ven_id AND s3.sej_uf_medicale_code = s2.sej_uf_medicale_code
    LEFT JOIN NOYAU.coeur.Uf uf ON s2.sej_uf_medicale_code = uf.uf_code
    INNER JOIN NOYAU.coeur.CENTRE_RESPONSABILITE cr ON cr.cr_id = uf.fk_cr_id
    LEFT JOIN DOMINHO.dominho.FICHE f ON f.fic_venue = s2.ven_id AND f.fic_suppr = 0
    LEFT JOIN NOYAU.coeur.CENTRE_RESPONSABILITE cr3 ON cr3.cr_code = f.centre_responsabilite_code
    LEFT JOIN dominho.dominho.DOSSIER_SPECIALITE ds ON ds.dossier_specialite_id = f.dossier_specialite_id
    INNER JOIN NOYAU.patient.patient p ON p.pat_id = f.patient_id
    LEFT JOIN (
        SELECT fhs2.fiche_id, Min(fhs2.fic_date_statut_validation) AS date_min_val
        FROM DOMINHO.dominho.FICHE_HISTORIQUE_STATUT fhs2
        WHERE fhs2.fic_statut_validation_id = 3
        GROUP BY fhs2.fiche_id
    ) AS fhs2 ON f.fiche_id = fhs2.fiche_id
    INNER JOIN DOMINHO.dominho.FORMULAIRE_SELECTION dfs ON f.formulaire_selection_id = dfs.formulaire_selection_id
        AND dfs.fos_libelle NOT LIKE '%HDJ%'
        AND dfs.fos_libelle NOT LIKE '%extraction%'
    LEFT JOIN dominho.dominho.FORMULAIRE fo ON dfs.formulaire_id = fo.formulaire_id
        AND (fo.type_document_code = '00209' OR fo.type_document_code = '00082')
        AND for_courrier = 1
    LEFT JOIN [dominho].[dominho].[DOSSIER_SPECIALITE_SPECIALITE] dss ON dss.dossier_specialite_id = ds.dossier_specialite_id
    LEFT JOIN [dominho].[dominho].[CENTRE_RESPONSABILITE_SPECIALITE] crs ON crs.specialite_code = dss.specialite_code
    LEFT JOIN noyau.coeur.CENTRE_RESPONSABILITE cr4 ON cr4.cr_code = crs.centre_responsabilite_code
    LEFT JOIN BOITE_ENVOI.BOITE_ENVOI.DOCUMENT EDOC ON EDOC.document_id = f.document_id
    LEFT JOIN BOITE_ENVOI.BOITE_ENVOI.DESTINATAIRE EDES ON EDES.doc_id = EDOC.doc_id
WHERE
    {venue_condition if venue_condition else date_condition}
    AND date_min_val >= dateAdd(Day, -1, cast(s3.date_der AS date))
    AND date_min_val <= DateAdd(Day, 5, Cast(s2.sej_date_sortie AS date))
    AND (
        CASE
            WHEN s1.sej_date_entree >= ven_admission THEN datediff(day, s1.sej_date_entree, s2.sej_date_sortie)
            WHEN s1.sej_date_entree < ven_admission THEN datediff(day, ven_admission, s2.sej_date_sortie)
        END
    ) >= 1
    AND (
        cr.cr_libelle_long = cr3.cr_libelle_long
        OR Cr.cr_libelle_long = cr4.cr_libelle_long
        OR (cr.cr_libelle_long = 'NEUROCHIRURGIE' AND ds.dos_libelle_court = 'NRDT Foch')
        OR (cr.cr_libelle_long = 'ANESTHESIE' AND ds.dos_libelle_court = 'Obstétrique')
    )
    AND ((fo.type_document_code IN ('00209')) OR (fo.type_document_code = '00082' AND s2.sej_uf_medicale_code IN ('290A', '294U')))
    AND (format(p.pat_date_deces, 'yyyy/MM/dd') > format(s2.sej_date_sortie, 'yyyy/MM/dd') OR p.pat_date_deces IS NULL)
    """

    # Partie 2 avec syntaxe corrigée aussi
    sql_query_part2 = f"""
UNION

/*Sans venue*/
SELECT DISTINCT TOP 5000
    year(s2.sej_date_sortie) AS annee,
    DateName(Month, s2.sej_date_sortie) AS mois,
    datediff(day, s2.sej_date_sortie, date_min_val) AS LL_J0,
    CASE
        WHEN s1.sej_date_entree >= ven_admission THEN datediff(day, s1.sej_date_entree, s2.sej_date_sortie)
        WHEN s1.sej_date_entree < ven_admission THEN datediff(day, ven_admission, s2.sej_date_sortie)
    END AS nuit_1,
    p.pat_ipp AS pat_IPP,
    p.pat_date_deces,
    v.ven_id,
    f.fiche_id,
    s1.sej_date_entree,
    s1.sej_uf_medicale_code,
    s3.date_der AS sej_date_der_entree,
    s2.sej_date_sortie AS sej_date_sortie,
    s2.sej_uf_medicale_code AS uf_der_pass,
    cr.cr_libelle_court AS cr_der_sej,
    CASE
        WHEN f.fic_venue IS NULL THEN 0
        WHEN f.fic_venue IS NOT NULL THEN v.ven_numero
    END AS Num_Venue,
    v.ven_numero AS ven_theo,
    cr3.cr_libelle_long AS CR_courrier,
    dfs.fos_libelle AS Type_courrier,
    ds.dos_libelle_court AS Dos_Spe_ESL,
    CASE
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Vasculaire Foch' THEN 'VASCULAIRE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Urologique Foch' THEN 'UROLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Réa Foch' THEN 'REANIMATION'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison ORL Foch' THEN 'ORL'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Oncologie Foch' THEN 'ONCOLOGIE'
        WHEN dfs.fos_libelle ='CR HDJ Oncologie Foch' THEN 'ONCOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Digestive Foch' THEN 'DIGESTIF'
        WHEN dfs.fos_libelle ='CR HDJ Endoscopie Digestive Foch' THEN 'ENDODIG'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Cardiologie Foch' THEN 'CARDIOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Unité Vanderbilt Foch ' THEN 'VANDERBILDT'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison UPHU Foch ' THEN 'UPHU'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Throm Foch' THEN 'NEUROLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Throm SG Foch' THEN 'NEUROLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Foch DOG' THEN 'OBSTETRIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Pédiatrie Foch' THEN 'NEONATOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Gynécologie Foch' THEN 'GYNECOLOGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Thoracique Foch' THEN 'THORACIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Chirurgie Thoracique Foch' AND ds.dos_libelle_court = 'Chirurgie Thoracique Foch' THEN 'THORACIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison USIR Foch ' AND ds.dos_libelle_court = 'Chirurgie Thoracique Foch' THEN 'THORACIQUE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Gériatrie Foch' THEN 'GERIATRIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison M.P.R Foch' THEN 'MPR'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison SSPI Foch' THEN 'ANESTHESIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Médecine interne et Polyvalente Foch'THEN 'MEDECINE INTERNE ET POLYVALENTE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Diabétologie Foch ' THEN 'MEDECINE INTERNE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison NRDT Foch' THEN 'NEUROCHIRURGIE'
        WHEN dfs.fos_libelle ='CR Lettre de Liaison Neurochirurgie Foch' THEN 'NEUROCHIRURGIE'
        WHEN dfs.fos_libelle ='CR Urgences' THEN 'URGENCES'
        ELSE cr4.cr_libelle_long
    END AS CR_Doss_spe,
    f.fic_date_creation,
    f.fic_date_modification,
    fhs2.date_min_val,
    convert(Varchar, EDES.dest_diffusion_date, 103) as 'Date diffusion',
    CASE EDES.st_id
        WHEN 1 THEN 'A diffuser'
        WHEN 3 THEN 'Echec'
        WHEN 4 THEN 'Diffuse'
        WHEN 7 THEN 'Annule'
        ELSE 'Pas dans boite envoi'
    END as 'Statut Envoi'
FROM
    NOYAU.patient.patient p
    LEFT JOIN DOMINHO.dominho.FICHE f ON p.pat_id = f.patient_id AND f.fic_venue IS NULL AND f.fic_suppr = 0
    INNER JOIN NOYAU.coeur.CENTRE_RESPONSABILITE cr3 ON cr3.cr_code = f.centre_responsabilite_code
    LEFT JOIN dominho.dominho.DOSSIER_SPECIALITE ds ON ds.dossier_specialite_id = f.dossier_specialite_id
    LEFT JOIN [dominho].[dominho].[DOSSIER_SPECIALITE_SPECIALITE] dss ON dss.dossier_specialite_id = ds.dossier_specialite_id
    LEFT JOIN [dominho].[dominho].[CENTRE_RESPONSABILITE_SPECIALITE] crs ON crs.specialite_code = dss.specialite_code
    LEFT JOIN noyau.coeur.CENTRE_RESPONSABILITE cr4 ON cr4.cr_code = crs.centre_responsabilite_code
    LEFT JOIN (
        SELECT fhs2.fiche_id, Min(fhs2.fic_date_statut_validation) AS date_min_val
        FROM DOMINHO.dominho.FICHE_HISTORIQUE_STATUT fhs2
        WHERE fhs2.fic_statut_validation_id = 3
        GROUP BY fhs2.fiche_id
    ) AS fhs2 ON f.fiche_id = fhs2.fiche_id
    INNER JOIN DOMINHO.dominho.FORMULAIRE_SELECTION dfs ON f.formulaire_selection_id = dfs.formulaire_selection_id
        AND dfs.fos_libelle NOT LIKE '%HDJ%'
        AND dfs.fos_libelle NOT LIKE '%extraction%'
    INNER JOIN dominho.dominho.FORMULAIRE fo ON dfs.formulaire_id = fo.formulaire_id
        AND fo.type_document_code IN ('00209', '00082')
        AND for_courrier = 1
    LEFT JOIN NOYAU.patient.VENUE v ON p.pat_id = v.pat_id AND v.pat_id = f.patient_id AND v.ven_supprime != 1
    AND ven_type IN (1)
    LEFT JOIN NOYAU.patient.SEJOUR s1 ON s1.ven_id = v.ven_id AND v.ven_supprime != 1 AND s1.sej_numero = '1'
    LEFT JOIN NOYAU.patient.SEJOUR s2 ON s2.ven_id = v.ven_id AND v.ven_supprime != 1
    AND s2.sej_est_dernier_sejour = 1
    LEFT JOIN (
        SELECT s.ven_id, MIN(s.sej_date_entree) AS date_der, s.sej_uf_medicale_code
        FROM NOYAU.patient.SEJOUR s
        INNER JOIN noyau.patient.sejour s2 ON s.ven_id = s2.ven_id
            AND s.sej_uf_medicale_code = s2.sej_uf_medicale_code
            AND s2.sej_est_dernier_sejour = 1
        GROUP BY s.ven_id, s.sej_uf_medicale_code
    ) AS s3 ON s3.ven_id = s2.ven_id
    LEFT JOIN NOYAU.coeur.Uf uf ON uf.uf_code = s2.sej_uf_medicale_code
    INNER JOIN NOYAU.coeur.CENTRE_RESPONSABILITE cr ON uf.fk_cr_id = cr.cr_id
    LEFT JOIN BOITE_ENVOI.BOITE_ENVOI.DOCUMENT EDOC ON EDOC.document_id = f.document_id
    LEFT JOIN BOITE_ENVOI.BOITE_ENVOI.DESTINATAIRE EDES ON EDES.doc_id = EDOC.doc_id
WHERE
    {date_condition}
    AND date_min_val >= DateAdd(Day, -1, Cast(s3.date_der AS date))
    AND date_min_val <= DateAdd(Day, 5, Cast(s2.sej_date_sortie AS date))
    AND date_min_val IS NOT NULL
    AND (
        CASE
            WHEN s1.sej_date_entree >= ven_admission THEN datediff(day, s1.sej_date_entree, s2.sej_date_sortie)
            WHEN s1.sej_date_entree < ven_admission THEN datediff(day, ven_admission, s2.sej_date_sortie)
        END
    ) >= 1
    AND (
        cr.cr_libelle_long = cr3.cr_libelle_long
        OR Cr.cr_libelle_long = cr4.cr_libelle_long
        OR (cr.cr_libelle_long = 'NEUROCHIRURGIE' AND ds.dos_libelle_court = 'NRDT Foch')
        OR (cr.cr_libelle_long = 'ANESTHESIE' AND ds.dos_libelle_court = 'Obstétrique')
    )
    AND ((fo.type_document_code IN ('00209')) OR (fo.type_document_code = '00082'
    AND s2.sej_uf_medicale_code IN ('290A', '294U')))
    AND (format(p.pat_date_deces, 'yyyy/MM/dd') > format(s2.sej_date_sortie, 'yyyy/MM/dd')
      OR p.pat_date_deces IS NULL)
    """

    # Requête SQL complète
    sql_query = sql_query_part1
    if include_second_part:
        sql_query += sql_query_part2

    try:
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        results = clean_query_results(rows, columns)
        return results
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'exécution de la requête: {str(e)}",
        ) from None
    finally:
        cursor.close()

# Routes de l'API Easily (identiques mais avec logging réduit)
@app.get("/api/patients/comptes-rendus", response_model=list[PatientRecord])
def get_patient_reports(
    start_date: Annotated[str | None, Query(description="Date de début (format YYYY-MM-DD)")] = None,
    end_date: Annotated[str | None, Query(description="Date de fin (format YYYY-MM-DD)")] = None,
    venues: Annotated[str | None, Query(description="Liste de numéros de séjour séparés par des virgules")] = None,
):
    try:
        # Validation des dates
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Format de date de début invalide. Utilisez YYYY-MM-DD",
                )

        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Format de date de fin invalide. Utilisez YYYY-MM-DD",
                )

        # Obtenir une connexion à la base de données
        conn = get_db_connection()
        results = execute_query(conn, start_date, end_date, venues)
        conn.close()

        # Convertir les résultats bruts en instances du modèle PatientRecord
        processed_results = []
        for item in results:
            item_copy = item.copy()

            # Nettoyer les valeurs nulles
            if item_copy.get("CR_Doss_spe") is None:
                item_copy["CR_Doss_spe"] = ""
            if item_copy.get("CR_courrier") is None:
                item_copy["CR_courrier"] = ""
            if item_copy.get("Type_courrier") is None:
                item_copy["Type_courrier"] = ""
            if item_copy.get("Dos_Spe_ESL") is None:
                item_copy["Dos_Spe_ESL"] = ""
            if item_copy.get("Statut Envoi") is None:
                item_copy["Statut Envoi"] = ""

            try:
                record = PatientRecord(**item_copy)
                processed_results.append(record)
            except Exception as validation_error:
                logger.warning(f"Erreur validation: {validation_error}")
                continue

        return processed_results
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from None

# Point d'entrée avec configuration optimisée
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="error",
        access_log=False,
        timeout_keep_alive=10,
        timeout_graceful_shutdown=5,
        limit_concurrency=30,
        limit_max_requests=500
    )
