"""Tests des routes HTML de republication : création depuis la fiche source,
page de republication (copie/publication), passage en publié (avec avancement
de la Source), page de listing.
"""

from app.models import Article, Republication, Source


def _creer_source_avec_article(test_db, *, statut: str = "digested") -> tuple[int, int]:
    db = test_db()
    source = Source(url=None, titre="Titre", contenu_brut="Contenu.", statut=statut)
    db.add(source)
    db.commit()
    db.refresh(source)

    article = Article(
        source_id=source.id, titre="Article", contenu="Contenu.", resume="Résumé."
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    source_id, article_id = source.id, article.id
    db.close()
    return source_id, article_id


def _creer_republication(test_db, article_id: int, *, statut: str = "draft") -> int:
    db = test_db()
    republication = Republication(
        article_id=article_id,
        canal="linkedin",
        brouillon="Mon brouillon.",
        posture="personal_branding",
        statut=statut,
    )
    db.add(republication)
    db.commit()
    db.refresh(republication)
    republication_id = republication.id
    db.close()
    return republication_id


def test_fiche_republier_cree_et_redirige(client, test_db):
    source_id, _ = _creer_source_avec_article(test_db)

    r = client.post(
        f"/liste/{source_id}/republier",
        data={
            "canal": "linkedin",
            "posture": "personal_branding",
            "brouillon": "Un point de vue sur ce sujet.",
        },
        follow_redirects=False,
    )

    assert r.status_code == 303
    republication_id = int(r.headers["location"].rsplit("/", 1)[-1])

    db = test_db()
    republication = db.get(Republication, republication_id)
    assert republication.canal == "linkedin"
    assert republication.posture == "personal_branding"
    assert republication.brouillon == "Un point de vue sur ce sujet."
    assert republication.statut == "draft"
    db.close()


def test_fiche_republier_sans_article_404(client, test_db):
    db = test_db()
    source = Source(url=None, titre="Sans article", statut="captured")
    db.add(source)
    db.commit()
    db.refresh(source)
    source_id = source.id
    db.close()

    r = client.post(
        f"/liste/{source_id}/republier",
        data={"canal": "linkedin", "posture": "personal_branding", "brouillon": "x"},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"

    db = test_db()
    assert db.query(Republication).count() == 0
    db.close()


def test_republication_detail_200(client, test_db):
    _, article_id = _creer_source_avec_article(test_db)
    republication_id = _creer_republication(test_db, article_id)

    r = client.get(f"/republications/{republication_id}")

    assert r.status_code == 200
    assert "Mon brouillon." in r.text


def test_republication_introuvable_404(client):
    r = client.get("/republications/999999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Republication introuvable"


def test_republication_publier(client, test_db):
    source_id, article_id = _creer_source_avec_article(test_db)
    republication_id = _creer_republication(test_db, article_id)

    r = client.post(
        f"/republications/{republication_id}/publier", follow_redirects=False
    )

    assert r.status_code == 303
    assert r.headers["location"] == f"/republications/{republication_id}"

    db = test_db()
    assert db.get(Republication, republication_id).statut == "published"
    assert db.get(Source, source_id).statut == "published"
    db.close()


def test_republication_publier_ne_recule_pas_le_statut(client, test_db):
    """Une Source déjà republiée puis re-publiée ailleurs ne recule pas de statut."""
    source_id, article_id = _creer_source_avec_article(test_db, statut="published")
    republication_id = _creer_republication(test_db, article_id)

    r = client.post(f"/republications/{republication_id}/publier")

    assert r.status_code in (200, 303)
    db = test_db()
    assert db.get(Source, source_id).statut == "published"
    db.close()


def test_republication_publier_introuvable_404(client, test_db):
    r = client.post("/republications/999999/publier")

    assert r.status_code == 404
    assert r.json()["detail"] == "Republication introuvable"

    db = test_db()
    assert db.query(Republication).count() == 0
    db.close()


def test_republication_publier_deja_publiee(client, test_db):
    """Republier une Republication déjà "published" : idempotent, pas de doublon.

    Ni ``publier_republication`` (statut réaffecté à la même valeur) ni
    ``avancer_statut`` (ne recule/ré-avance jamais) ne traitent ce cas comme
    une erreur : ce test fige ce comportement volontairement permissif.
    """
    source_id, article_id = _creer_source_avec_article(test_db, statut="published")
    republication_id = _creer_republication(test_db, article_id, statut="published")

    r = client.post(
        f"/republications/{republication_id}/publier", follow_redirects=False
    )

    assert r.status_code == 303

    db = test_db()
    assert db.query(Republication).filter_by(article_id=article_id).count() == 1
    republication = db.get(Republication, republication_id)
    assert republication.statut == "published"
    assert db.get(Source, source_id).statut == "published"
    db.close()


def test_liste_republications_200(client, test_db):
    _, article_id = _creer_source_avec_article(test_db)
    _creer_republication(test_db, article_id)

    r = client.get("/republications")

    assert r.status_code == 200
    assert "linkedin" in r.text


def test_liste_republications_vide(client):
    r = client.get("/republications")

    assert r.status_code == 200
    assert "Aucune republication" in r.text
