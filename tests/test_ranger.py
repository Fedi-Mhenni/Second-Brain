"""Tests de ``PATCH /sources/{id}/folder`` (Ranger) : rangement, non-régression
du statut, 404 Source, 404 Folder.
"""

from app.models import Folder, Source


def _creer_source(test_db, statut: str = "captured") -> int:
    db = test_db()
    source = Source(url=None, titre="Test", contenu_brut="Contenu.", statut=statut)
    db.add(source)
    db.commit()
    db.refresh(source)
    source_id = source.id
    db.close()
    return source_id


def _creer_folder(test_db, nom: str = "Technique") -> int:
    db = test_db()
    folder = Folder(nom=nom)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    folder_id = folder.id
    db.close()
    return folder_id


def test_ranger_source_captured_vers_folder(client, test_db):
    source_id = _creer_source(test_db, statut="captured")
    folder_id = _creer_folder(test_db)

    r = client.patch(f"/sources/{source_id}/folder", json={"folder_id": folder_id})

    assert r.status_code == 200
    corps = r.json()
    assert corps["statut"] == "ranged"
    assert corps["folder_id"] == folder_id


def test_ranger_source_digested_ne_recule_pas(client, test_db):
    source_id = _creer_source(test_db, statut="digested")
    folder_id = _creer_folder(test_db)

    r = client.patch(f"/sources/{source_id}/folder", json={"folder_id": folder_id})

    assert r.status_code == 200
    corps = r.json()
    assert corps["statut"] == "digested"  # pas de retour en arrière vers "ranged"
    assert corps["folder_id"] == folder_id  # le dossier est quand même affecté


def test_ranger_source_introuvable(client, test_db):
    folder_id = _creer_folder(test_db)

    r = client.patch("/sources/999999/folder", json={"folder_id": folder_id})

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"


def test_ranger_folder_introuvable(client, test_db):
    source_id = _creer_source(test_db)

    r = client.patch(f"/sources/{source_id}/folder", json={"folder_id": 999999})

    assert r.status_code == 404
    assert r.json()["detail"] == "Folder introuvable"
