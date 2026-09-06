"""Tests de ``GET /folders`` : listing trié par nom, gestion de ``description=None``."""

from app.models import Folder


def _creer_folder(test_db, nom: str, description: str | None = None) -> None:
    db = test_db()
    db.add(Folder(nom=nom, description=description))
    db.commit()
    db.close()


def test_folders_liste_triee_par_nom(client, test_db):
    # Insérés dans le désordre pour vérifier que le tri vient bien de la route.
    _creer_folder(test_db, "Technique")
    _creer_folder(test_db, "Carrière & Mindset", description="Posture pro")
    _creer_folder(test_db, "Design & UX/UI")

    r = client.get("/folders")

    assert r.status_code == 200
    noms = [f["nom"] for f in r.json()]
    assert noms == ["Carrière & Mindset", "Design & UX/UI", "Technique"]
    assert noms == sorted(noms)


def test_folders_description_none_ne_plante_pas(client, test_db):
    _creer_folder(test_db, "Sans description", description=None)

    r = client.get("/folders")

    assert r.status_code == 200
    entree = next(f for f in r.json() if f["nom"] == "Sans description")
    assert entree["description"] is None
