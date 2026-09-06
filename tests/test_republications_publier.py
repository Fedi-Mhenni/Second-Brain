"""Tests de PATCH /republications/{id}/publier : passage en "published" (avec
avancement de la Source), 404 sur Republication inexistante.
"""

from app.models import Article, Republication, Source


def _creer_republication(test_db, *, statut_source: str = "digested") -> tuple[int, int]:
    db = test_db()
    source = Source(
        url=None, titre="Titre", contenu_brut="Contenu.", statut=statut_source
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    article = Article(
        source_id=source.id, titre="Article", contenu="Contenu.", resume="Résumé."
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    republication = Republication(
        article_id=article.id,
        canal="linkedin",
        brouillon="Mon brouillon.",
        posture="personal_branding",
    )
    db.add(republication)
    db.commit()
    db.refresh(republication)

    source_id, republication_id = source.id, republication.id
    db.close()
    return source_id, republication_id


def test_publier_republication_nominal(client, test_db):
    """Statut de la Republication -> "published", Source avancée au même statut."""
    source_id, republication_id = _creer_republication(test_db)

    r = client.patch(f"/republications/{republication_id}/publier")

    assert r.status_code == 200
    corps = r.json()
    assert corps["id"] == republication_id
    assert corps["statut"] == "published"
    assert corps["canal"] == "linkedin"
    assert corps["posture"] == "personal_branding"

    db = test_db()
    assert db.get(Republication, republication_id).statut == "published"
    assert db.get(Source, source_id).statut == "published"
    db.close()


def test_publier_republication_introuvable_404(client):
    r = client.patch("/republications/999999/publier")

    assert r.status_code == 404
    assert r.json() == {"detail": "Republication introuvable"}
