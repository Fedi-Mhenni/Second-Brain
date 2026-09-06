"""Insère les dossiers de base. Relançable sans créer de doublon.

Lancement : ``python -m scripts.seed`` depuis la racine du projet.
Dans Docker : ``docker compose exec app python -m scripts.seed``.
"""

from app.database import SessionLocal, init_db
from app.models import Folder

# Les dossiers thématiques de départ, propres à cette instance.
DOSSIERS = [
    {
        "nom": "Technique",
        "description": (
            "Axe 1 - TECHNOLOGIQUE. Outils, langages et frameworks pour "
            "developper des agents et automatiser."
        ),
    },
    {
        "nom": "Intelligence artificielle",
        "description": (
            "Axe 2 - TECHNOLOGIQUE. Modeles, agents autonomes, capacites "
            "reelles et limites documentees."
        ),
    },
    {
        "nom": "Trading & finance",
        "description": (
            "Axe 3 - METIER. Marches, strategies, outils d'analyse et cadre "
            "reglementaire."
        ),
    },
    {
        "nom": "UX / UI Design",
        "description": (
            "Axe 4 - FONCTIONNEL. Interfaces, ergonomie et attentes reelles "
            "des utilisateurs."
        ),
    },
    {
        "nom": "Business & entrepreneuriat",
        "description": (
            "Axe 5 - METIER. Modeles economiques, marche de l'IA, "
            "opportunites professionnelles."
        ),
    },
    {
        "nom": "Gestion de projet digital",
        "description": (
            "Axe 6 - METIER. Methodes, roles et outillage de la conduite de "
            "projet numerique."
        ),
    },
]

NOMS = [dossier["nom"] for dossier in DOSSIERS]


def seed() -> None:
    """Crée les dossiers de ``NOMS`` qui ne sont pas déjà en base."""
    init_db()  # crée les tables si la base est vierge

    db = SessionLocal()
    try:
        crees, existants = [], []
        for dossier in DOSSIERS:
            nom = dossier["nom"]
            description = dossier["description"]
            # ``.first()`` renvoie la ligne ou None : on ne crée que si absente.
            folder = db.query(Folder).filter_by(nom=nom).first()
            if folder is None:
                db.add(Folder(nom=nom, description=description))
                crees.append(nom)
            else:
                if not folder.description:
                    folder.description = description
                existants.append(nom)
        db.commit()
    finally:
        db.close()

    print(f"{len(crees)} créé(s) : {crees}")
    print(f"{len(existants)} déjà présent(s) : {existants}")


if __name__ == "__main__":
    seed()
