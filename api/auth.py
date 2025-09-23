# auth.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel
import os
import json
import bcrypt
from dotenv import load_dotenv
from pathlib import Path
import logging
from typing import Optional


SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"

dotenv_path = Path(__file__).resolve().parent / "easily" / ".env"
load_dotenv(dotenv_path=dotenv_path)

admin_users_json = os.getenv("ADMIN_USERS")
if admin_users_json is not None:
    ADMIN_USERS = json.loads(admin_users_json)

user_roles_json = os.getenv("USER_ROLES")
if user_roles_json:
    USER_ROLES = json.loads(user_roles_json)

class UserInfo(BaseModel):
    username: str
    expires_at: datetime
    roles: list

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fonction pour créer un token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserInfo:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        exp = payload.get("exp")
        if not username or not exp:
            raise HTTPException(status_code=401, detail="Invalid token")
        expiration_time = datetime.utcfromtimestamp(exp)
        roles = USER_ROLES.get(username, [])
        return UserInfo(username=username, expires_at=expiration_time, roles=roles)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

log_file = "user_connections.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

def record_user_login(user):
    # Enregistrement de la connexion dans les logs
    logging.info(f"User {user} connected.")