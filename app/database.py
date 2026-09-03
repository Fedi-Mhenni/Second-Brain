"""Connexion à la base SQLite et création des tables.

Ce module centralise tout ce qui touche à la base de données :
- ``engine``       : le point d'entrée SQLAlchemy vers le fichier SQLite ;
- ``SessionLocal`` : une fabrique de sessions (une session = une conversation avec la base) ;
- ``Base``         : la classe mère dont hériteront tous les modèles ;
- ``get_db()``     : la dépendance FastAPI qui fournit une session puis la referme ;
- ``init_db()``    : crée les tables au démarrage si elles n'existent pas encore.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Charge les variables du fichier .env dans l'environnement du processus.
load_dotenv()

# URL de connexion. Par défaut : un fichier ``second_brain.db`` à la racine du projet.
# Chaque membre du binôme a ainsi sa propre base locale (cf. cadrage : une instance par personne).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./second_brain.db")

# ``check_same_thread=False`` est spécifique à SQLite : par défaut SQLite interdit
# d'utiliser une connexion depuis un autre thread que celui qui l'a créée, or FastAPI
# peut traiter les requêtes sur plusieurs threads. On lève donc cette restriction.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Fabrique de sessions. ``autocommit``/``autoflush`` à False = comportement explicite :
# rien n'est écrit dans la base tant qu'on n'appelle pas ``commit()``.
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Classe de base commune à tous les modèles. SQLAlchemy s'en sert pour recenser
# les tables déclarées (dans ``Base.metadata``).
Base = declarative_base()


def utcnow() -> datetime:
    """Date/heure courante en UTC (avec fuseau).

    Sert de valeur par défaut aux colonnes ``created_at`` / ``updated_at`` des
    modèles. Placée ici pour éviter de la dupliquer dans chaque fichier de modèle.
    """
    return datetime.now(timezone.utc)


def get_db():
    """Fournit une session de base de données à une route, puis la referme.

    Utilisation dans une route FastAPI : ``db: Session = Depends(get_db)``.
    Le ``yield`` passe la session à la route ; le bloc ``finally`` garantit la
    fermeture même si la route lève une exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crée toutes les tables déclarées sur ``Base`` si elles n'existent pas encore.

    L'import des modèles est fait ici (et pas en haut du fichier) pour éviter un
    import circulaire : ``app/models/*.py`` importe ``Base`` depuis ce module.
    Importer le paquet ``app.models`` a un effet de bord : chaque classe de modèle
    s'enregistre sur ``Base.metadata``, ce qui permet à ``create_all`` de connaître
    les tables à créer.
    """
    from app import models  # noqa: F401  (import pour effet de bord)

    Base.metadata.create_all(bind=engine)
