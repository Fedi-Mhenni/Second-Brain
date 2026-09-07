"""Configuration centralisée, lue depuis les variables d'environnement.

Toute lecture de ``os.getenv`` pour une variable de configuration doit passer
par ce module plutôt que d'être dispersée dans le code métier.
"""

import os

from dotenv import load_dotenv

# Charge les variables du fichier .env dans l'environnement du processus.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/second_brain.db")

# Profil de veille de l'instance : court texte qui oriente le ton et les angles
# des résumés générés par l'IA (injecté dans le prompt Gemini, voir
# app/services/llm_provider.py). Chaque personne qui fait tourner sa propre
# instance peut le personnaliser via l'environnement, sans toucher au code.
_PROFIL_VEILLE_DEFAUT = "un développeur qui fait sa veille technique et professionnelle"

# ``or`` plutôt que le 2e argument de ``os.getenv`` : la valeur par défaut doit
# aussi s'appliquer quand PROFIL_VEILLE est présent mais vide — c'est le cas de
# ``.env.example``, qui livre la ligne ``PROFIL_VEILLE=`` (chaîne vide, pas None).
PROFIL_VEILLE = (os.getenv("PROFIL_VEILLE") or "").strip() or _PROFIL_VEILLE_DEFAUT
