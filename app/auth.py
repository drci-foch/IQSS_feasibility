import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import streamlit as st

# ===== CONFIGURATION INTÉGRÉE =====
# Utilisateurs autorisés (format: "username": "sha256_hash_of_password")
AUTHORIZED_USERS = {
    "admin": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # password: admin123
}

# Rôles et permissions
USER_ROLES = {
    "admin": ["full_access", "easily", "lifen", "analysis"],
}

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


def check_password(username: str, password: str) -> bool:
    """Vérifie si le mot de passe est correct pour l'utilisateur donné"""
    if username not in AUTHORIZED_USERS:
        return False
    return AUTHORIZED_USERS[username] == hash_password(password)


def get_user_permissions(username: str) -> list:
    """Retourne les permissions de l'utilisateur"""
    return USER_ROLES.get(username, [])


def is_session_valid() -> bool:
    """Vérifie si la session est valide et non expirée"""
    if "authenticated" not in st.session_state:
        return False

    if "login_time" not in st.session_state:
        return False

    # Utiliser la durée de session configurée
    if datetime.now() - st.session_state.login_time > SESSION_DURATION:
        return False

    return st.session_state.authenticated


def logout():
    """Déconnecte l'utilisateur"""
    for key in list(st.session_state.keys()):
        if key.startswith(("authenticated", "username", "user_permissions", "login_time")):
            del st.session_state[key]
    st.rerun()


def get_css_styles() -> str:
    """Retourne les styles CSS corrigés pour garder le contenu dans la bulle"""
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
        
        /* Reset Streamlit styles qui interfèrent */
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
        
        /* Container principal de login - TOUT le contenu doit être dedans */
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
            /* Assurer que le contenu reste dans le container */
            contain: layout style;
            text-align: center;
            color: var(--primary-blue-dark);
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            line-height: 1;
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
        
        /* TOUS les éléments dans le container doivent avoir position relative et z-index > 1 */
        .login-container > * {
            position: relative;
            z-index: 1;
        }
        
        /* En-tête - DANS le container */
        .login-header {
            text-align: center;
            color: var(--primary-blue-dark);
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }
        
        .login-subtitle {
            text-align: center;
            color: var(--text-light);
            font-size: 1rem;
            font-weight: 400;
            margin: 0 0 2rem 0;
            line-height: 1.4;
        }
        
        /* Formulaire - DANS le container */
        .login-form {
            margin: 1.5rem 0;
            width: 100%;
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
        
        /* Bouton de connexion - DANS le container */
        .login-button-container {
            margin: 1.5rem 0;
            text-align: center;
            width: 100%;
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
        
        /* Messages d'état - DANS le container */
        .stAlert {
            border-radius: 8px !important;
            border: none !important;
            box-shadow: var(--shadow-light) !important;
            margin: 1rem 0 !important;
        }
        
        /* Pied de page - DANS le container */
        .footer-info {
            text-align: center;
            margin: 2rem 0 0 0;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-light);
            font-size: 0.85rem;
        }
        
        .footer-info p {
            margin: 0.25rem 0;
        }
        
        .hospital-name {
            font-weight: 600;
            color: var(--primary-blue);
        }
        
        /* Section démo - DANS le container si activée */
        .demo-info {
            background: linear-gradient(135deg, var(--primary-blue-light) 0%, #f0f8ff 100%);
            border-left: 4px solid var(--secondary-green);
            padding: 1.25rem;
            margin: 1.5rem 0;
            border-radius: 0 var(--border-radius) var(--border-radius) 0;
            box-shadow: var(--shadow-light);
            width: 100%;
            box-sizing: border-box;
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
            
            .login-header {
                font-size: 2.2rem;
            }
            
            .login-subtitle {
                font-size: 0.95rem;
            }
        }
        
        /* Styles pour les success/error messages */
        .stSuccess {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%) !important;
            color: #155724 !important;
        }
        
        .stError {
            background: linear-gradient(135deg, #f8d7da 0%, #f1b0b7 100%) !important;
            color: #721c24 !important;
        }
        
        .stWarning {
            background: linear-gradient(135deg, #fff3cd 0%, #fce8b2 100%) !important;
            color: #856404 !important;
        }
        
        .stInfo {
            background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%) !important;
            color: #0c5460 !important;
        }
        
        /* Force tous les éléments Streamlit à rester dans le container */
        .login-container .stTextInput,
        .login-container .stButton,
        .login-container .stAlert,
        .login-container .stSuccess,
        .login-container .stError,
        .login-container .stWarning,
        .login-container .stInfo {
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
        }
    </style>
    """


def render_demo_accounts():
    """Affiche la section des comptes de démonstration avec un design amélioré"""
    st.markdown(
        """
        <div class="demo-info">
            <h4>🔧 Comptes de démonstration disponibles</h4>
    """,
        unsafe_allow_html=True,
    )

    demo_accounts = [
        {
            "title": "👨‍💼 Administrateur complet",
            "username": "admin",
            "password": "admin123",
            "description": "Accès à toutes les fonctionnalités",
            "icon": "🔧",
        },
    ]

    for account in demo_accounts:
        st.markdown(
            f"""
            <div class="demo-account">
                <div class="demo-account-title">
                    {account["icon"]} {account["title"]}
                </div>
                <div style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;">
                    {account["description"]}
                </div>
                <div class="demo-credentials">
                    Utilisateur: <strong>{account["username"]}</strong><br>
                    Mot de passe: <strong>{account["password"]}</strong>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_login_page() -> None:
    """Affiche la page de connexion avec design corrigé"""

    # Injection des styles CSS
    st.markdown(get_css_styles(), unsafe_allow_html=True)

    # Conteneur principal - TOUT doit être à l'intérieur
    # En-tête - DANS le container
    st.markdown(
        """
        <div class="login-container">SEQUAD</div>
        <div class="login-subtitle">Sécurité, Évaluation et Qualité des Données<br>
        <strong>Hôpital Foch - DRCI</strong></div>
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
            # Simulation d'un petit délai pour le feedback visuel
            with st.spinner("Vérification des identifiants..."):
                time.sleep(0.5)  # Petit délai pour l'UX

            if check_password(username, password):
                # Connexion réussie
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_permissions = get_user_permissions(username)
                st.session_state.login_time = datetime.now()

                st.success(AUTH_MESSAGES["login_success"].format(username=username))

                # Affichage des permissions accordées
                permissions = get_user_permissions(username)
                if permissions:
                    permission_names = {
                        "full_access": "Administration complète",
                        "easily": "Données Easily",
                        "lifen": "Données Lifen",
                        "analysis": "Analyses avancées",
                    }
                    perm_list = [permission_names.get(p, p) for p in permissions]
                    st.info(f"🔐 **Accès autorisés :** {', '.join(perm_list)}")

                time.sleep(2)
                st.rerun()
            else:
                st.error(AUTH_MESSAGES["login_failed"])
        else:
            st.warning("⚠️ Veuillez remplir tous les champs")

    # Section des comptes de démonstration - DANS le container si activée
    if SHOW_DEMO_ACCOUNTS:
        render_demo_accounts()

    # Pied de page - DANS le container
    st.markdown(
        """
        <div class="footer-info">
            <p><span class="hospital-name">🏥 Hôpital Foch - Unité Data - DRCI</span></p>
            <p>Outil d'analyse des lettres de liaison patients</p>
            <p><em>Version 2.0 - 2025</em></p>
            <p><em>Sarra Ben Yahia</em></p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Fermeture du container - TOUT doit être au-dessus de cette ligne
    st.markdown("</div>", unsafe_allow_html=True)


def render_user_info():
    """Affiche les informations de l'utilisateur connecté dans la sidebar avec design amélioré"""
    if "username" in st.session_state:
        st.sidebar.markdown(get_css_styles(), unsafe_allow_html=True)

        # Container avec style amélioré
        st.sidebar.markdown(
            f"""
            <div class="user-info-container">
                <div class="user-info-header">
                    👤 Utilisateur connecté
                </div>
                <div class="user-name">{st.session_state.username}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


        # Informations de session améliorées
        if "login_time" in st.session_state:
            session_time = datetime.now() - st.session_state.login_time
            hours = int(session_time.total_seconds() // 3600)
            minutes = int((session_time.total_seconds() % 3600) // 60)

            # Calcul du temps restant
            time_left = SESSION_DURATION - session_time
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() // 3600)
                minutes_left = int((time_left.total_seconds() % 3600) // 60)

                session_status = "🟢 Active"
                if hours_left < 1:
                    session_status = "🟡 Expire bientôt"

                st.sidebar.markdown(
                    f"""
                    <div class="session-info">
                        <strong>{session_status}</strong><br>
                        ⏰ Reste: {hours_left}h {minutes_left}m
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.sidebar.error("🔴 Session expirée")

        st.sidebar.markdown("<br>", unsafe_allow_html=True)

        # Bouton de déconnexion amélioré
        if st.sidebar.button("🚪 Se déconnecter", type="secondary", use_container_width=True):
            logout()


def check_permission(required_permission: str) -> bool:
    """Vérifie si l'utilisateur a la permission requise"""
    if not is_session_valid():
        return False

    user_permissions = st.session_state.get("user_permissions", [])
    return required_permission in user_permissions or "full_access" in user_permissions


def require_auth():
    """Décorateur pour protéger une fonction avec authentification"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_session_valid():
                render_login_page()
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def show_permission_denied(required_permission: str):
    """Affiche un message d'erreur de permission avec style amélioré"""
    st.error(AUTH_MESSAGES["insufficient_permissions"])
    st.info(f"🔐 **Permission requise :** {required_permission}")

    # Suggestions d'amélioration de compte
    current_permissions = st.session_state.get("user_permissions", [])
    if current_permissions:
        st.info(f"📋 **Vos permissions actuelles :** {', '.join(current_permissions)}")


def show_toast(message: str, type_msg: str = "info"):
    """Affiche une notification toast"""
    if type_msg == "success":
        st.success(message)
    elif type_msg == "error":
        st.error(message)
    elif type_msg == "warning":
        st.warning(message)
    else:
        st.info(message)