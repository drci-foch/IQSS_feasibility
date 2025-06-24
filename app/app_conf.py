import os

# Configuration des APIs
EASILY_API_URL = os.getenv(
    "EASILY_API_URL", "http://localhost:8000/api/patients/comptes-rendus"
)
LIFEN_API_URL = os.getenv("LIFEN_API_URL", "http://localhost:8001/api/lifen/data")
