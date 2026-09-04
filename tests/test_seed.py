"""Test de non-duplication du seed : relancer ``seed()`` ne doit rien dupliquer.

Note : contrairement à ``test_health.py``, ce test écrit réellement dans la
base configurée par ``DATABASE_URL`` (même mécanisme que ``scripts/seed.py``
en usage normal) — il n'y a pas encore d'infrastructure de base de test
isolée dans le projet.
"""

from app.database import SessionLocal
from app.models import Folder
from scripts.seed import NOMS, seed


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
