"""Test de non-duplication du seed : relancer ``seed()`` ne doit rien dupliquer.

Note : contrairement à ``test_health.py``, ce test écrit réellement dans la
base configurée par ``DATABASE_URL`` (même mécanisme que ``scripts/seed.py``
en usage normal) — il n'y a pas encore d'infrastructure de base de test
isolée dans le projet.
"""

from app.database import SessionLocal
from app.models import Folder
from scripts.seed import DOSSIERS, NOMS, seed


def test_seed_est_idempotent():
    # Deux lancements à la suite : le second ne doit créer aucun doublon,
    # que la base soit vierge ou déjà seedée avant ce test.
    seed()
    seed()

    db = SessionLocal()
    try:
        for nom in NOMS:
            assert db.query(Folder).filter_by(nom=nom).count() == 1
    finally:
        db.close()


def test_seed_renseigne_les_descriptions_manquantes():
    db = SessionLocal()
    try:
        folder = db.query(Folder).filter_by(nom="Technique").first()
        if folder is None:
            db.add(Folder(nom="Technique", description=None))
        else:
            folder.description = None
        db.commit()
    finally:
        db.close()

    seed()

    description_attendue = next(
        dossier["description"] for dossier in DOSSIERS if dossier["nom"] == "Technique"
    )
    db = SessionLocal()
    try:
        folder = db.query(Folder).filter_by(nom="Technique").one()
        assert folder.description == description_attendue
    finally:
        db.close()
