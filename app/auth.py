import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import requests
from app_conf import AUTH_LOGIN_API_URL, AUTH_VALIDATE_API_URL, DECONNEXION_API_URL
import jwt
import streamlit.components.v1 as components

import streamlit as st

session = requests.Session()

# Configuration de session
SESSION_DURATION = timedelta(hours=3)

# Messages d'interface
AUTH_MESSAGES = {
    "login_success": "✅ Connexion réussie ! Bienvenue {username}",
    "login_failed": "❌ Nom d'utilisateur ou mot de passe incorrect",
    "session_expired": "⏰ Votre session a expiré. Veuillez vous reconnecter.",
    "insufficient_permissions": "⚠️ Vous n'avez pas les permissions nécessaires pour cette action",
    "account_locked": "🔒 Compte temporairement verrouillé suite à trop de tentatives",
}

# Configuration d'affichage
SHOW_DEMO_ACCOUNTS = False


def hash_password(password: str) -> str:
    """Hache un mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def logout_storage():
    components.html(
        """
    <script>
        localStorage.removeItem("access_token");
        window.parent.location.reload();
    </script>
    """,
        height=0,
    )
    st.stop()


def logout():
    """Déconnecte l'utilisateur"""
    api_request("POST", DECONNEXION_API_URL)
    logout_storage()


def api_request(method, url, **kwargs):
    token = st.session_state.get("access_token")

    response = requests.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    if response.status_code == 401:
        st.warning("🚫 Accès non autorisé (401).")
        logout_storage()
        return None

    return response


def is_logged_in():
    token = st.session_state.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(AUTH_VALIDATE_API_URL, headers=headers)

    print(response.status_code)
    print("iciii")
    if response.status_code == 200:
        print(response.json())
        st.session_state.username = response.json().get("username")
        st.session_state.authenticated = True
        st.session_state.user_permissions = response.json().get("roles", [])
        st.session_state.login_time = response.json().get("remaining_seconds")
        return True
    else:
        st.session_state.username = None
    return False


def store_token(token):
    import streamlit.components.v1 as components

    components.html(
        f"""
    <script>
        localStorage.setItem("access_token", "{token}");
        window.parent.location.reload();
    </script>
    """,
        height=0,
    )


def get_css_styles() -> str:
    """Retourne les styles CSS avec le logo intégré"""
    return """
    <style>
        /* Variables CSS */
        :root {
            --primary-blue: #0066cc;
            --primary-blue-dark: #004499;
            --primary-blue-light: #e6f3ff;
            --secondary-green: #00c851;
            --accent-orange: #ff8800;
            --text-dark: #2c3e50;
            --text-light: #7f8c8d;
            --background-light: #f8f9fa;
            --border-color: #e9ecef;
            --shadow-light: 0 2px 10px rgba(0,0,0,0.08);
            --shadow-medium: 0 4px 20px rgba(0,0,0,0.12);
            --border-radius: 12px;
            --transition: all 0.3s ease;
        }
        
        /* Reset Streamlit styles */
        .main .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 500px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Masquer les éléments Streamlit par défaut */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        
        /* Container principal de login */
        .login-container {
            width: 100%;
            max-width: 420px;
            margin: 0 auto;
            padding: 2.5rem 2rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-medium);
            background: #ffffff;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
            box-sizing: border-box;
            contain: layout style;
            text-align: center;
        }

        /* Barre de gradient en haut */
        .login-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-blue-dark) 0%, var(--secondary-green) 100%);
            z-index: 1;
        }
        
        /* Container du logo EXTÉRIEUR - en dehors de la bulle */
        .logo-container-outside {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 2rem;
            position: relative;
            z-index: 3;
        }
        
        /* Styles du logo - VERSION GRANDE */
        .hospital-logo-large {
            max-height: 120px;
            max-width: 300px;
            width: auto;
            height: auto;
            object-fit: contain;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.15));
            transition: var(--transition);
        }
        
        .hospital-logo-large:hover {
            transform: scale(1.05);
            filter: drop-shadow(0 6px 12px rgba(0,0,0,0.2));
        }
        
        /* Titre de l'application - modifié pour s'harmoniser avec le logo */
        .app-title {
            color: var(--primary-blue-dark);
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            line-height: 1;
            margin: 0;
            position: relative;
            z-index: 2;
        }
        
        /* Sous-titre */
        .login-subtitle {
            text-align: center;
            color: var(--text-light);
            font-size: 1rem;
            font-weight: 400;
            margin: 1rem 0 2rem 0;
            line-height: 1.4;
        }
        
        .login-subtitle strong {
            color: var(--primary-blue);
            font-weight: 600;
        }
        
        /* Formulaire */
        .login-form {
            margin: 1.5rem 0;
            width: 100%;
            position: relative;
            z-index: 2;
        }
        
        /* Champs de saisie */
        .stTextInput {
            margin-bottom: 1rem;
        }
        
        .stTextInput > div > div > input {
            border-radius: 8px !important;
            border: 2px solid var(--border-color) !important;
            padding: 12px 16px !important;
            font-size: 16px !important;
            transition: var(--transition) !important;
            background-color: white !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: var(--primary-blue) !important;
            box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1) !important;
            outline: none !important;
        }
        
        .stTextInput > label {
            font-weight: 500 !important;
            color: var(--text-dark) !important;
            font-size: 14px !important;
            margin-bottom: 8px !important;
        }
        
        /* Bouton de connexion */
        .login-button-container {
            margin: 1.5rem 0;
            text-align: center;
            width: 100%;
            position: relative;
            z-index: 2;
        }
        
        .stButton > button {
            width: 100% !important;
            background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-blue-dark) 100%) !important;
            color: white !important;
            border: none !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            letter-spacing: 0.5px !important;
            transition: var(--transition) !important;
            box-shadow: var(--shadow-light) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: var(--shadow-medium) !important;
            background: linear-gradient(135deg, var(--primary-blue-dark) 0%, #003366 100%) !important;
        }
            
        .centered-button-container {
            display: flex;
            justify-content: center;
            margin: 1rem 0;
        }

        .centered-button-container .stButton > button {
            width: auto !important;
            min-width: 200px;
            padding: 0.75rem 2rem !important;
            text-align: center;
        }

        /* Messages d'état */
        .stAlert {
            border-radius: 8px !important;
            border: none !important;
            box-shadow: var(--shadow-light) !important;
            margin: 1rem 0 !important;
            position: relative;
            z-index: 2;
        }
        
        /* Pied de page */
        .footer-info {
            text-align: center;
            margin: 2rem 0 0 0;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-light);
            font-size: 0.85rem;
            position: relative;
            z-index: 2;
        }
        
        .footer-info p {
            margin: 0.25rem 0;
        }
        
        .hospital-name {
            font-weight: 600;
            color: var(--primary-blue);
        }
        
        /* Section démo */
        .demo-info {
            background: linear-gradient(135deg, var(--primary-blue-light) 0%, #f0f8ff 100%);
            border-left: 4px solid var(--secondary-green);
            padding: 1.25rem;
            margin: 1.5rem 0;
            border-radius: 0 var(--border-radius) var(--border-radius) 0;
            box-shadow: var(--shadow-light);
            width: 100%;
            box-sizing: border-box;
            position: relative;
            z-index: 2;
        }
        
        .demo-info h4 {
            color: var(--primary-blue);
            margin: 0 0 0.75rem 0;
            font-weight: 600;
            font-size: 1rem;
        }
        
        .demo-account {
            background-color: white;
            padding: 0.75rem;
            border-radius: 6px;
            margin: 0.5rem 0;
            border: 1px solid var(--border-color);
            transition: var(--transition);
        }
        
        .demo-account:hover {
            box-shadow: var(--shadow-light);
            transform: translateY(-1px);
        }
        
        .demo-account-title {
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 0.25rem;
            font-size: 0.9rem;
        }
        
        .demo-credentials {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 0.5rem;
            border-radius: 4px;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
            font-size: 13px;
            border: 1px solid var(--border-color);
            margin-top: 0.25rem;
        }
        
        .demo-credentials strong {
            color: var(--primary-blue);
            font-weight: 600;
        }
        
        /* Animation d'apparition */
        .login-container {
            animation: fadeIn 0.6s ease-out;
        }
        
        @keyframes fadeIn {
            from { 
                opacity: 0; 
                transform: translateY(20px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            
            .login-container {
                margin: 1rem auto;
                padding: 2rem 1.5rem;
                max-width: 95%;
            }
            
            .hospital-logo-large {
                max-height: 90px;
                max-width: 220px;
            }
            
            .app-title {
                font-size: 1.8rem;
            }
        }
        
        @media (max-width: 480px) {
            .hospital-logo-large {
                max-height: 70px;
                max-width: 180px;
            }
            
            .app-title {
                font-size: 1.5rem;
            }
        }
    </style>
    """


def check_permission(required_permission: str) -> bool:
    """Vérifie si l'utilisateur a une permission spécifique"""
    user_permissions = st.session_state.get("user_permissions", [])
    return required_permission in user_permissions


def render_user_info() -> None:
    """Affiche les informations utilisateur dans la sidebar"""
    with st.sidebar:
        if st.session_state.get("username"):
            st.success(f"🟢 Connecté: **{st.session_state.username}**")

            # Affichage du temps restant si disponible
            if st.session_state.get("login_time"):
                remaining_time = st.session_state.login_time
                hours = remaining_time // 3600
                minutes = (remaining_time % 3600) // 60
                st.info(f"⏰ Session: {hours}h {minutes}min restantes")

            # Bouton de déconnexion
            if st.button("🚪 Se déconnecter", key="logout_button"):
                logout()


def render_login_page() -> None:
    """Affiche la page de connexion avec design corrigé et logo"""

    # Injection des styles CSS
    st.markdown(get_css_styles(), unsafe_allow_html=True)
    if st.session_state.get("username") == None:
        st.markdown(
            """
            <style>
            .st-emotion-cache-zy6yx3 {
                width: 35% !important;
                max-width: 35% !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    # Logo en dehors de la bulle - plus grand
    st.markdown(
        """
        <div class="logo-container-outside">
            <img src="https://upload.wikimedia.org/wikipedia/fr/d/d4/Logo_HOPITAL_FOCH.png" 
                 alt="Logo Hôpital Foch" 
                 class="hospital-logo-large">
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Conteneur principal SEQUAD
    st.markdown(
        """
        <div class="login-container">
            <div class="app-title">SEQUAD</div>
        </div>
        <div class="login-subtitle">Sécurité, Évaluation et Qualité des Données<br>
        <strong>Hôpital Foch - DRCI - Unité Data</strong></div>
        """,
        unsafe_allow_html=True,
    )

    # Formulaire de connexion - DANS le container
    with st.form("login_form", clear_on_submit=False):
        st.markdown('<div class="login-form">', unsafe_allow_html=True)

        username = st.text_input(
            "👤 Nom d'utilisateur",
            placeholder="Entrez votre nom d'utilisateur",
            help="Utilisez un des comptes de démonstration ci-dessous",
        )
        password = st.text_input(
            "🔒 Mot de passe",
            type="password",
            placeholder="Entrez votre mot de passe",
            help="Le mot de passe est sensible à la casse",
        )

        # Bouton centré avec container personnalisé
        st.markdown('<div class="login-button-container">', unsafe_allow_html=True)
        login_button = st.form_submit_button("🚀 Se connecter", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Traitement de la connexion avec feedback amélioré - DANS le container
    if login_button:
        if username and password:
            data = {"username": username, "password": password}
            response = requests.post(f"{AUTH_LOGIN_API_URL}", data=data)

            if response.status_code == 200:
                st.success("Connexion réussie ! 🎉")
                store_token(response.json()["access_token"])
            elif response.status_code == 401:
                st.error("Utilisateur ou mot de passe invalide.")
            else:
                st.error(f"Erreur de connexion: {response.status_code}")
        else:
            st.warning("Veuillez remplir tous les champs.")

    # Pied de page - DANS le container
    st.markdown(
        """
        <div class="footer-info">
            <p><em>by Sarra Ben Yahia</em></p>

        </div>
        """,
        unsafe_allow_html=True,
    )
