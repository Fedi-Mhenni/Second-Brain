"""Tests des routes HTML de la fiche source (GET /liste/{id} et ses cinq
actions POST). Chaque action délègue à un service déjà couvert ailleurs
(test_qualifier.py, test_qualifier_auto.py, test_ranger.py, test_digest_auto.py) :
ici on vérifie seulement le branchement HTML (code retour, redirection, 404),
pas la logique métier elle-même.
"""

from app.models import Article, ArticleTag, Folder, Qualification, Republication, Source, Tag
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


def _creer_source_avec_article(test_db, *, statut: str = "digested") -> int:
    db = test_db()
    source = Source(url=None, titre="Titre", contenu_brut="Contenu.", statut=statut)
    db.add(source)
    db.commit()
    db.refresh(source)

    db.add(
        Article(source_id=source.id, titre="Article", contenu="Contenu.", resume="Résumé.")
    )
    db.commit()

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


# ---------------------------------------------------------------------------
# Chemins d'erreur : chaque cas vérifie le code retour ET l'absence d'effet
# de bord (rien créé/modifié en base, statut de la Source inchangé).
# ---------------------------------------------------------------------------


def test_fiche_ranger_folder_introuvable_404(client, test_db):
    """Folder_id valide (un entier) mais qui ne correspond à aucun Folder."""
    source_id = _creer_source(test_db)

    r = client.post(
        f"/liste/{source_id}/ranger",
        data={"folder_id": "999999"},
        follow_redirects=False,
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Folder introuvable"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.folder_id is None
    assert source.statut == "captured"
    db.close()


def test_fiche_ranger_folder_id_invalide_422(client, test_db):
    """Folder_id qui n'est même pas un entier : rejeté par FastAPI avant le service."""
    source_id = _creer_source(test_db)

    r = client.post(
        f"/liste/{source_id}/ranger",
        data={"folder_id": "pas-un-nombre"},
        follow_redirects=False,
    )

    assert r.status_code == 422

    db = test_db()
    source = db.get(Source, source_id)
    assert source.folder_id is None
    assert source.statut == "captured"
    db.close()


def test_fiche_ranger_source_introuvable_404(client, test_db):
    folder_id = _creer_folder(test_db)

    r = client.post(f"/liste/999999/ranger", data={"folder_id": str(folder_id)})

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"


def test_fiche_digerer_auto_sans_contenu_brut(client, test_db, monkeypatch):
    """Aucun contenu_brut à digérer : redirection avec erreur, rien créé.

    Le service vérifie l'absence de contenu avant tout appel au LLMProvider
    (voir app/services/digerer.py) : monkeypatch posé ici par prudence, pas
    parce que le provider est réellement sollicité sur ce chemin.
    """
    monkeypatch.setattr(
        "app.services.digerer.get_llm_provider", lambda: MockProvider()
    )
    source_id = _creer_source(test_db, contenu_brut=None)

    r = client.post(f"/liste/{source_id}/digerer/auto", follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}?erreur=aucun_contenu"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.article is None
    assert source.statut == "captured"
    db.close()


def test_fiche_digerer_auto_source_introuvable_404(client, test_db):
    r = client.post("/liste/999999/digerer/auto")

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(Article).count() == 0
    db.close()


def test_fiche_digerer_manuel_resume_vide_sans_article(client, test_db):
    """Résumé blanc, aucun Article existant : redirection avec erreur, aucun Article créé."""
    source_id = _creer_source(test_db)

    r = client.post(
        f"/liste/{source_id}/digerer", data={"resume": "   "}, follow_redirects=False
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}?erreur=resume_vide"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.article is None
    assert source.statut == "captured"
    db.close()


def test_fiche_digerer_manuel_resume_vide_avec_article_existant(client, test_db):
    """Résumé blanc envoyé sur une Source déjà digérée : le résumé existant n'est pas écrasé."""
    source_id = _creer_source(test_db)
    db = test_db()
    source = db.get(Source, source_id)
    source.statut = "digested"
    db.add(Article(source_id=source_id, resume="Résumé déjà enregistré."))
    db.commit()
    db.close()

    r = client.post(
        f"/liste/{source_id}/digerer", data={"resume": ""}, follow_redirects=False
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}?erreur=resume_vide"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.article.resume == "Résumé déjà enregistré."
    assert source.statut == "digested"
    db.close()


def test_fiche_digerer_source_introuvable_404(client, test_db):
    r = client.post("/liste/999999/digerer", data={"resume": "Un résumé."})

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(Article).count() == 0
    db.close()


def test_fiche_qualifier_source_introuvable_404(client, test_db):
    r = client.post(
        "/liste/999999/qualifier",
        data={"categorie": "pro", "legitimite": "4", "interet": "5"},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(Qualification).count() == 0
    db.close()


def test_fiche_qualifier_auto_source_introuvable_404(client, test_db):
    r = client.post("/liste/999999/qualifier/auto")

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(Qualification).count() == 0
    db.close()


def test_fiche_republier_source_introuvable_404(client, test_db):
    r = client.post(
        "/liste/999999/republier",
        data={"canal": "linkedin", "posture": "personal_branding", "brouillon": "x"},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(Republication).count() == 0
    db.close()


def test_fiche_tag_nominal(client, test_db):
    source_id = _creer_source_avec_article(test_db)

    r = client.post(
        f"/liste/{source_id}/tags",
        data={"nom": "Design", "added_by": "manual"},
        follow_redirects=False,
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/liste/{source_id}"

    db = test_db()
    assert db.query(Tag).filter_by(nom="Design").count() == 1
    assert db.query(ArticleTag).count() == 1
    db.close()


def test_fiche_tag_source_sans_article_404(client, test_db):
    source_id = _creer_source(test_db)  # sans article

    r = client.post(f"/liste/{source_id}/tags", data={"nom": "Design"})

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(ArticleTag).count() == 0
    db.close()


def test_fiche_tag_deux_fois_pas_de_doublon(client, test_db):
    source_id = _creer_source_avec_article(test_db)

    client.post(f"/liste/{source_id}/tags", data={"nom": "Design", "added_by": "manual"})
    r = client.post(
        f"/liste/{source_id}/tags",
        data={"nom": "Design", "added_by": "manual"},
        follow_redirects=False,
    )

    assert r.status_code == 303

    db = test_db()
    assert db.query(ArticleTag).count() == 1
    db.close()
