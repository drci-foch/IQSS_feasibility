import os

# Configuration des APIs
EASILY_API_URL = os.getenv("EASILY_API_URL", "http://localhost:8000/api/patients/comptes-rendus")
LIFEN_API_URL = os.getenv("LIFEN_API_URL", "http://localhost:8001/api/lifen/data")
AUTH_LOGIN_API_URL = os.getenv("AUTH_LOGIN_API_URL", "http://localhost:8000/token")
AUTH_VALIDATE_API_URL = os.getenv("AUTH_VALIDATE_API_URL", "http://localhost:8000/me")
DECONNEXION_API_URL = os.getenv("DECONNEXION_API_URL", "http://localhost:8000/logout")