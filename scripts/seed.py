"""Insère les dossiers de base. Relançable sans créer de doublon.

Lancement : ``python -m scripts.seed`` depuis la racine du projet.
Dans Docker : ``docker compose exec app python -m scripts.seed``.
"""

from app.database import SessionLocal, init_db
from app.models import Folder

# Les dossiers thématiques de départ, propres à cette instance.
NOMS = [
    "Technique",
    "Design & UX/UI",
    "Carrière & Mindset",
    "Tendances Numériques & IA",
    "Gestion de projet digital",
]


def seed() -> None:
    """Crée les dossiers de ``NOMS`` qui ne sont pas déjà en base."""
    init_db()  # crée les tables si la base est vierge

    db = SessionLocal()
    try:
        crees, existants = [], []
        for nom in NOMS:
            # ``.first()`` renvoie la ligne ou None : on ne crée que si absente.
            if db.query(Folder).filter_by(nom=nom).first() is None:
                db.add(Folder(nom=nom))
                crees.append(nom)
            else:
                existants.append(nom)
        db.commit()
    finally:
        db.close()

    print(f"{len(crees)} créé(s) : {crees}")
    print(f"{len(existants)} déjà présent(s) : {existants}")


if __name__ == "__main__":
    seed()
