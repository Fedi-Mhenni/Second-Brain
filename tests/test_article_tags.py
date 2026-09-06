"""Tests de POST/GET /articles/{id}/tags : création, réutilisation d'un Tag
existant, doublon de lien évité (avec conservation de l'added_by d'origine),
404 sur Article inexistant, added_by invalide en 422, listing (avec ou sans tag).
"""

from app.models import Article, ArticleTag, Source, Tag


def _creer_article(test_db, *, titre: str = "Article test") -> int:
    db = test_db()
    source = Source(url=None, titre=titre, contenu_brut="Contenu.", statut="digested")
    db.add(source)
    db.commit()
    db.refresh(source)

    article = Article(
        source_id=source.id, titre=titre, contenu="Contenu.", resume="Résumé."
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    article_id = article.id
    db.close()
    return article_id


def test_taguer_article_cree_le_tag(client, test_db):
    article_id = _creer_article(test_db)

    r = client.post(
        f"/articles/{article_id}/tags",
        json={"nom": "IA générative", "added_by": "manual"},
    )

    assert r.status_code == 201
    corps = r.json()
    assert corps["nom"] == "IA générative"
    assert corps["added_by"] == "manual"

    db = test_db()
    assert db.query(Tag).filter_by(nom="IA générative").count() == 1
    assert db.query(ArticleTag).filter_by(article_id=article_id).count() == 1
    db.close()


def test_taguer_added_by_defaut_manual(client, test_db):
    """``added_by`` omis dans le body : "manual" par défaut."""
    article_id = _creer_article(test_db)

    r = client.post(f"/articles/{article_id}/tags", json={"nom": "Veille"})

    assert r.status_code == 201
    assert r.json()["added_by"] == "manual"


def test_taguer_reutilise_tag_existant(client, test_db):
    """Deux Articles tagués du même mot partagent la même ligne Tag."""
    article_id_1 = _creer_article(test_db, titre="Article 1")
    article_id_2 = _creer_article(test_db, titre="Article 2")

    client.post(f"/articles/{article_id_1}/tags", json={"nom": "Carrière"})
    r = client.post(f"/articles/{article_id_2}/tags", json={"nom": "Carrière"})

    assert r.status_code == 201

    db = test_db()
    assert db.query(Tag).filter_by(nom="Carrière").count() == 1
    assert db.query(ArticleTag).count() == 2
    db.close()


def test_taguer_meme_tag_deux_fois_pas_de_doublon(client, test_db):
    article_id = _creer_article(test_db)

    client.post(
        f"/articles/{article_id}/tags", json={"nom": "Design", "added_by": "manual"}
    )
    r = client.post(
        f"/articles/{article_id}/tags", json={"nom": "Design", "added_by": "manual"}
    )

    assert r.status_code == 201

    db = test_db()
    assert db.query(ArticleTag).filter_by(article_id=article_id).count() == 1
    db.close()


def test_taguer_lien_existant_added_by_different_pas_ecrase(client, test_db):
    """Un lien confirmé manuellement n'est pas repris par une suggestion IA identique."""
    article_id = _creer_article(test_db)

    client.post(
        f"/articles/{article_id}/tags", json={"nom": "Produit", "added_by": "manual"}
    )
    r = client.post(
        f"/articles/{article_id}/tags", json={"nom": "Produit", "added_by": "ai"}
    )

    assert r.status_code == 201
    assert r.json()["added_by"] == "manual"

    db = test_db()
    assert db.query(ArticleTag).filter_by(article_id=article_id).count() == 1
    lien = db.query(ArticleTag).filter_by(article_id=article_id).one()
    assert lien.added_by == "manual"
    db.close()


def test_taguer_article_introuvable_404(client, test_db):
    r = client.post("/articles/999999/tags", json={"nom": "x"})

    assert r.status_code == 404
    assert r.json() == {"detail": "Article introuvable"}

    db = test_db()
    assert db.query(Tag).count() == 0
    db.close()


def test_taguer_added_by_invalide_422(client, test_db):
    article_id = _creer_article(test_db)

    r = client.post(
        f"/articles/{article_id}/tags", json={"nom": "x", "added_by": "robot"}
    )

    assert r.status_code == 422

    db = test_db()
    assert db.query(Tag).count() == 0
    db.close()


def test_lister_tags_article_vide(client, test_db):
    article_id = _creer_article(test_db)

    r = client.get(f"/articles/{article_id}/tags")

    assert r.status_code == 200
    assert r.json() == []


def test_lister_tags_article(client, test_db):
    article_id = _creer_article(test_db)
    client.post(f"/articles/{article_id}/tags", json={"nom": "A", "added_by": "manual"})
    client.post(f"/articles/{article_id}/tags", json={"nom": "B", "added_by": "ai"})

    r = client.get(f"/articles/{article_id}/tags")

    assert r.status_code == 200
    noms = {tag["nom"] for tag in r.json()}
    assert noms == {"A", "B"}


def test_lister_tags_article_introuvable_404(client):
    r = client.get("/articles/999999/tags")

    assert r.status_code == 404
    assert r.json() == {"detail": "Article introuvable"}
