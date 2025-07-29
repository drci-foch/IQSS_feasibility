# IQSS Feasibility

Une application d'analyse automatiques des IQSS, développée avec FastAPI et Streamlit pour faciliter l'évaluation.

## 🚀 Technologies

- **Backend**: FastAPI avec Uvicorn
- **Frontend**: Streamlit
- **Base de données**: Oracle DB, SQL Server (via pyodbc)
- **Analyse de données**: Pandas, Plotly
- **Gestion de projet**: Poetry
- **Qualité du code**: MyPy, Ruff

## 📋 Fonctionnalités

- Interface web intuitive pour l'analyse de faisabilité
- Connexion aux bases de données hospitalières (Oracle, SQL Server)
- Visualisations interactives avec Plotly
- Export des résultats en Excel
- API REST pour l'intégration avec d'autres systèmes

## 🛠️ Installation

### Prérequis

- Python 3.8+
- Poetry (recommandé) ou pip
- Accès aux bases de données Oracle/SQL Server configurées

### Installation avec Poetry (recommandé)

```bash
# Cloner le repository
git clone https://github.com/drci-foch/IQSS_feasibility.git
cd IQSS_feasibility

# Installer les dépendances
poetry install

# Activer l'environnement virtuel
poetry shell
```

### Installation avec pip

```bash
# Cloner le repository
git clone https://github.com/drci-foch/IQSS_feasibility.git
cd IQSS_feasibility

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -e .
```

## ⚙️ Configuration

1.1 **Variables d'environnement** : Créez un fichier `.env` dans api/easily :

```env
DB_CONNECTION_STRING=DRIVER={SQL Server};SERVER={server};DATABASE={database};UID={id};PWD={password};TrustServerCertificate=yes
```

1.2 **Variables d'environnement** : Créez un fichier `.env` dans api/lifen :

```env
ORACLE_USER={user}
ORACLE_PASSWORD={pswd}
ORACLE_DSN={driver}
```


## 🚀 Utilisation

### Lancement de l'application Streamlit

```bash
# Avec Poetry
poetry run streamlit run main.py

# Avec pip
python -m streamlit run main.py
```

L'application sera accessible sur http://localhost:8501

### Lancement de l'API FastAPI

```bash
# Avec Poetry
pythin api/run_all.py
```

L'API Easily sera accessible sur http://localhost:8000
- Documentation interactive : http://localhost:8000/docs
- Documentation ReDoc : http://localhost:8000/redoc

L'API Easily sera accessible sur http://localhost:8001
- Documentation interactive : http://localhost:8001/docs
- Documentation ReDoc : http://localhost:8001/redoc


## 📁 Structure du projet

```
IQSS_feasibility/
├── api/                    # API FastAPI (8 fichiers)
│   ├── main.py            # Point d'entrée de l'API
│   ├── routes/            # Routes et endpoints
│   └── models/            # Modèles de données
├── app/                    # Application Streamlit (24 fichiers)
│   ├── pages/             # Pages de l'interface
│   ├── components/        # Composants réutilisables
│   └── utils/             # Fonctions utilitaires
├── sql_scripts/           # Scripts SQL pour les requêtes
├── main.py               # Point d'entrée principal
├── pyproject.toml        # Configuration Poetry et dépendances
└── README.md
```

## 🔧 Développement

### Qualité du code

```bash
# Vérification des types avec MyPy
poetry run mypy .

# Formatage et linting avec Ruff
poetry run ruff check .
poetry run ruff format .
```

### Tests

```bash
# Lancer les tests (si configurés)
poetry run pytest
```

## 🤝 Contribution

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Committez vos changements (`git commit -m 'Ajout d'une nouvelle fonctionnalité'`)
4. Poussez vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrez une Pull Request

## 📝 Changelog

Voir les [commits récents](https://github.com/drci-foch/IQSS_feasibility/commits/main) pour les dernières modifications.

## 📄 Licence

Ce projet est développé par l'équipe DRCI de l'Hôpital Foch pour les besoins internes de recherche clinique.

## 🆘 Support

Pour toute question ou problème :
- Ouvrez une [issue](https://github.com/drci-foch/IQSS_feasibility/issues) sur GitHub
- Contactez l'équipe de développement DRCI

---

**Version**: 0.1.0  
**Dernière mise à jour**: 2025