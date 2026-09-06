"""Configuration centralisée, lue depuis les variables d'environnement.

Toute lecture de ``os.getenv`` pour une variable de configuration doit passer
par ce module plutôt que d'être dispersée dans le code métier.
"""

import os

from dotenv import load_dotenv

# Charge les variables du fichier .env dans l'environnement du processus.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/second_brain.db")
