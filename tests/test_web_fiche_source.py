"""Tests des routes HTML de la fiche source (GET /liste/{id} et ses cinq
actions POST). Chaque action délègue à un service déjà couvert ailleurs
(test_qualifier.py, test_qualifier_auto.py, test_ranger.py, test_digest_auto.py) :
ici on vérifie seulement le branchement HTML (code retour, redirection, 404),
pas la logique métier elle-même.
"""

from app.models import Folder, Qualification, Source
from app.services.llm_provider import MockProvider


def _creer_source(test_db, *, statut: str = "captured", contenu_brut: str = "Contenu.") -> int:
    db = test_db()
    source = Source(url=None, titre="Titre", contenu_brut=contenu_brut, statut=statut)
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


def test_fiche_source_200(client, test_db):
    source_id = _creer_source(test_db)

    r = client.get(f"/liste/{source_id}")

    assert r.status_code == 200
    assert "Pas encore qualifiée" in r.text


def test_fiche_source_introuvable_404(client):
    r = client.get("/liste/999999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"


def test_fiche_qualifier_manuel(client, test_db):
    source_id = _creer_source(test_db)

    r = client.post(
        f"/liste/{source_id}/qualifier",
        data={"categorie": "pro", "legitimite": "4", "interet": "5"},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}"

    db = test_db()
    assert db.query(Qualification).filter_by(source_id=source_id).count() == 1
    assert db.get(Source, source_id).statut == "qualified"
    db.close()


def test_fiche_qualifier_auto(client, test_db, monkeypatch):
    monkeypatch.setattr(
        "app.services.qualifier.get_llm_provider", lambda: MockProvider()
    )
    source_id = _creer_source(test_db)

    r = client.post(f"/liste/{source_id}/qualifier/auto", follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}"

    db = test_db()
    assert db.query(Qualification).filter_by(source_id=source_id).count() == 1
    db.close()


def test_fiche_ranger(client, test_db):
    source_id = _creer_source(test_db)
    folder_id = _creer_folder(test_db)

    r = client.post(
        f"/liste/{source_id}/ranger",
        data={"folder_id": str(folder_id)},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}"

    db = test_db()
    assert db.get(Source, source_id).folder_id == folder_id
    db.close()


def test_fiche_digerer_auto(client, test_db, monkeypatch):
    monkeypatch.setattr(
        "app.services.digerer.get_llm_provider", lambda: MockProvider()
    )
    source_id = _creer_source(
        test_db, contenu_brut="Un contenu assez long à résumer automatiquement."
    )

    r = client.post(f"/liste/{source_id}/digerer/auto", follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.statut == "digested"
    assert source.article is not None
    db.close()


def test_fiche_digerer_manuel(client, test_db):
    source_id = _creer_source(test_db)

    r = client.post(
        f"/liste/{source_id}/digerer",
        data={"resume": "Mon résumé manuel."},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.article.resume == "Mon résumé manuel."
    assert source.statut == "digested"
    db.close()
