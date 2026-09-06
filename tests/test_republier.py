"""Tests de POST /articles/{id}/republications : 404 sur article inexistant,
création, plusieurs republications sur le même Article sans conflit, canal
et posture invalides en 422.
"""

from app.models import Article, Republication, Source


def _creer_article(test_db) -> int:
    """Insère une Source puis son Article directement en base (la route de
    digestion du coéquipier n'est pas encore disponible ici), renvoie l'id
    de l'Article.
    """
    db = test_db()
    source = Source(url=None, titre="Test", contenu_brut="Contenu.", statut="digested")
    db.add(source)
    db.commit()
    db.refresh(source)

    article = Article(
        source_id=source.id, titre="Article test", contenu="Contenu.", resume="Résumé."
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    article_id = article.id
    db.close()
    return article_id


def test_republier_article_introuvable(client):
    """404 si l'Article n'existe pas."""
    r = client.post(
        "/articles/9999/republications",
        json={
            "canal": "linkedin",
            "brouillon": "Un brouillon.",
            "posture": "personal_branding",
        },
    )

    assert r.status_code == 404
    assert r.json() == {"detail": "Article introuvable"}


def test_republier_cree_la_republication(client, test_db):
    """Création : statut "draft" par défaut, champs renvoyés tels quels."""
    article_id = _creer_article(test_db)

    r = client.post(
        f"/articles/{article_id}/republications",
        json={
            "canal": "linkedin",
            "brouillon": "Mon brouillon.",
            "posture": "personal_branding",
        },
    )

    assert r.status_code == 201
    corps = r.json()
    assert corps["article_id"] == article_id
    assert corps["canal"] == "linkedin"
    assert corps["brouillon"] == "Mon brouillon."
    assert corps["posture"] == "personal_branding"
    assert corps["statut"] == "draft"

    db = test_db()
    assert db.query(Republication).filter_by(article_id=article_id).count() == 1
    db.close()


def test_republier_plusieurs_fois_sans_conflit(client, test_db):
    """Deux republications du même Article (canaux différents) : aucun conflit, deux lignes."""
    article_id = _creer_article(test_db)

    r1 = client.post(
        f"/articles/{article_id}/republications",
        json={
            "canal": "linkedin",
            "brouillon": "Version LinkedIn.",
            "posture": "personal_branding",
        },
    )
    r2 = client.post(
        f"/articles/{article_id}/republications",
        json={"canal": "x", "brouillon": "Version X.", "posture": "entreprise"},
    )

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]

    db = test_db()
    assert db.query(Republication).filter_by(article_id=article_id).count() == 2
    db.close()


def test_republier_canal_invalide(client, test_db):
    """Canal hors de la liste Literal : rejeté par Pydantic, 422."""
    article_id = _creer_article(test_db)

    r = client.post(
        f"/articles/{article_id}/republications",
        json={"canal": "facebook", "brouillon": "x", "posture": "personal_branding"},
    )

    assert r.status_code == 422


def test_republier_posture_invalide(client, test_db):
    """Posture hors de la liste Literal : rejetée par Pydantic, 422."""
    article_id = _creer_article(test_db)

    r = client.post(
        f"/articles/{article_id}/republications",
        json={"canal": "linkedin", "brouillon": "x", "posture": "bidon"},
    )

    assert r.status_code == 422
