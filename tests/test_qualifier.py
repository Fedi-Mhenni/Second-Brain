"""Tests de POST /sources/{id}/qualification : création, mise à jour sans
doublon, 404, validation Pydantic (categorie/bornes), avancement de statut
dans les deux sens.
"""

from app.models import Qualification, Source


def _creer_source(test_db, statut: str = "captured") -> int:
    """Insère une Source directement en base et renvoie son id."""
    db = test_db()
    source = Source(
        url=None, titre="Test", contenu_brut="Contenu de test.", statut=statut
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    source_id = source.id
    db.close()
    return source_id


def test_qualifier_source_introuvable(client):
    """404 si la Source n'existe pas."""
    r = client.post(
        "/sources/9999/qualification",
        json={"categorie": "pro", "legitimite": 3, "interet": 4},
    )

    assert r.status_code == 404
    assert r.json() == {"detail": "Source introuvable"}


def test_qualifier_cree_la_qualification(client, test_db):
    """Première qualification : crée la ligne, avance le statut, qualified_by par défaut."""
    source_id = _creer_source(test_db)

    r = client.post(
        f"/sources/{source_id}/qualification",
        json={"categorie": "metier", "legitimite": 4, "interet": 5},
    )

    assert r.status_code == 200
    corps = r.json()
    assert corps["source_id"] == source_id
    assert corps["categorie"] == "metier"
    assert corps["legitimite"] == 4
    assert corps["interet"] == 5
    assert corps["qualified_by"] == "manual"

    db = test_db()
    assert db.query(Qualification).filter_by(source_id=source_id).count() == 1
    assert db.get(Source, source_id).statut == "qualified"
    db.close()


def test_qualifier_met_a_jour_sans_dupliquer(client, test_db):
    """Une 2e qualification de la même Source met à jour la ligne, n'en crée pas une 2e."""
    source_id = _creer_source(test_db)

    client.post(
        f"/sources/{source_id}/qualification",
        json={"categorie": "pro", "legitimite": 2, "interet": 2},
    )
    r = client.post(
        f"/sources/{source_id}/qualification",
        json={
            "categorie": "culture",
            "legitimite": 5,
            "interet": 1,
            "qualified_by": "ai",
        },
    )

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] == "culture"
    assert corps["legitimite"] == 5
    assert corps["interet"] == 1
    assert corps["qualified_by"] == "ai"

    db = test_db()
    assert db.query(Qualification).filter_by(source_id=source_id).count() == 1
    db.close()


def test_qualifier_categorie_invalide(client, test_db):
    """Categorie hors de la liste Literal : rejetée par Pydantic, 422."""
    source_id = _creer_source(test_db)

    r = client.post(
        f"/sources/{source_id}/qualification",
        json={"categorie": "inconnue", "legitimite": 3, "interet": 3},
    )

    assert r.status_code == 422


def test_qualifier_note_hors_bornes(client, test_db):
    """Note hors 1-5 : rejetée par Pydantic, 422 (le service n'est jamais appelé)."""
    source_id = _creer_source(test_db)

    r = client.post(
        f"/sources/{source_id}/qualification",
        json={"categorie": "pro", "legitimite": 6, "interet": 3},
    )

    assert r.status_code == 422


def test_qualifier_avance_le_statut_si_anterieur(client, test_db):
    """Source "captured" (avant "qualified" dans STATUTS) : le statut avance."""
    source_id = _creer_source(test_db, statut="captured")

    client.post(
        f"/sources/{source_id}/qualification",
        json={"categorie": "pro", "legitimite": 3, "interet": 3},
    )

    db = test_db()
    assert db.get(Source, source_id).statut == "qualified"
    db.close()


def test_qualifier_ne_recule_pas_le_statut(client, test_db):
    """Source "ranged" (après "qualified" dans STATUTS) : le statut ne recule pas."""
    source_id = _creer_source(test_db, statut="ranged")

    client.post(
        f"/sources/{source_id}/qualification",
        json={"categorie": "pro", "legitimite": 3, "interet": 3},
    )

    db = test_db()
    assert db.get(Source, source_id).statut == "ranged"
    db.close()
