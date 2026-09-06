"""Tests de ``GET /sources`` : listing complet trié par ``created_at`` décroissant,
filtres ``?statut=`` / ``?folder_id=`` isolés puis cumulés, statut inexistant.
"""

from datetime import datetime, timedelta, timezone

from app.models import Folder, Source

# Base d'horodatage : chaque Source reçoit un ``created_at`` explicite et distinct
# (``_BASE`` + N minutes), pour un tri déterministe sans dépendre de la vitesse
# d'exécution des insertions.
_BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _creer_folder(test_db, nom: str) -> int:
    db = test_db()
    folder = Folder(nom=nom)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    folder_id = folder.id
    db.close()
    return folder_id


def _creer_source(test_db, *, statut: str, ordre: int, folder_id: int | None = None) -> int:
    db = test_db()
    source = Source(
        url=None,
        titre=f"S{ordre}",
        contenu_brut="c",
        statut=statut,
        folder_id=folder_id,
        created_at=_BASE + timedelta(minutes=ordre),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    source_id = source.id
    db.close()
    return source_id


def test_sources_sans_filtre_triees_created_at_desc(client, test_db):
    s0 = _creer_source(test_db, statut="captured", ordre=0)
    s1 = _creer_source(test_db, statut="captured", ordre=1)
    s2 = _creer_source(test_db, statut="ranged", ordre=2)

    r = client.get("/sources")

    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [s2, s1, s0]  # plus récent en premier


def test_sources_filtre_statut(client, test_db):
    _creer_source(test_db, statut="captured", ordre=0)
    ranged = _creer_source(test_db, statut="ranged", ordre=1)

    r = client.get("/sources", params={"statut": "ranged"})

    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [ranged]


def test_sources_filtre_folder_id(client, test_db):
    f1 = _creer_folder(test_db, "F1")
    f2 = _creer_folder(test_db, "F2")
    _creer_source(test_db, statut="ranged", ordre=0, folder_id=f1)
    dans_f2 = _creer_source(test_db, statut="ranged", ordre=1, folder_id=f2)

    r = client.get("/sources", params={"folder_id": f2})

    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [dans_f2]


def test_sources_filtres_cumules_et(client, test_db):
    f1 = _creer_folder(test_db, "F1")
    _creer_source(test_db, statut="ranged", ordre=0, folder_id=f1)
    _creer_source(test_db, statut="ranged", ordre=1, folder_id=f1)
    cible = _creer_source(test_db, statut="digested", ordre=2, folder_id=f1)
    _creer_source(test_db, statut="digested", ordre=3, folder_id=None)  # bon statut, pas dans f1

    r = client.get("/sources", params={"statut": "digested", "folder_id": f1})

    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [cible]


def test_sources_statut_inexistant_liste_vide(client, test_db):
    _creer_source(test_db, statut="captured", ordre=0)

    r = client.get("/sources", params={"statut": "banane"})

    assert r.status_code == 200
    assert r.json() == []
