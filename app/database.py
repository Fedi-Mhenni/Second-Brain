"""Connexion à la base SQLite et création des tables.

Ce module centralise tout ce qui touche à la base de données :
- ``engine``       : le point d'entrée SQLAlchemy vers le fichier SQLite ;
- ``SessionLocal`` : une fabrique de sessions (une session = une conversation avec la base) ;
- ``Base``         : la classe mère dont hériteront tous les modèles ;
- ``get_db()``     : la dépendance FastAPI qui fournit une session puis la referme ;
- ``init_db()``    : crée les tables au démarrage si elles n'existent pas encore.
"""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# Le dossier ``data/`` ne sert qu'au fichier SQLite local (dev). Sur un déploiement
# comme Vercel, le système de fichiers est en lecture seule et DATABASE_URL pointe
# vers Postgres (Supabase) : créer ce dossier dans ce cas planterait le démarrage
# pour rien, d'où le garde-fou.
if DATABASE_URL.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)

# ``check_same_thread=False`` ne concerne que SQLite : par défaut SQLite interdit
# d'utiliser une connexion depuis un autre thread que celui qui l'a créée, or FastAPI
# peut traiter les requêtes sur plusieurs threads. Sur un autre SGBD, cet argument
# n'existe pas -> on ne le passe que si l'URL est une URL SQLite.
connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(DATABASE_URL, connect_args=connect_args)

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
