"""Tests de ``POST /sources/{id}/qualification/auto`` (qualification via LLMProvider).

Le provider est remplacé par un faux objet dont ``generer`` renvoie une
réponse fixée par chaque test (voir ``_FauxProvider``) : aucun appel réseau,
et chaque cas de réponse malformée est testé indépendamment.
"""

from app.models import Qualification, Source


class _FauxProvider:
    """Faux LLMProvider : ``generer`` renvoie la réponse fixée à la construction."""

    def __init__(self, reponse: str):
        self._reponse = reponse

    def generer(self, prompt: str) -> str:
        return self._reponse


def _forcer_provider(monkeypatch, reponse: str) -> None:
    """Remplace ``get_llm_provider`` tel qu'importé par app.services.qualifier."""
    monkeypatch.setattr(
        "app.services.qualifier.get_llm_provider", lambda: _FauxProvider(reponse)
    )


def _creer_source(test_db, *, statut: str = "captured") -> int:
    db = test_db()
    source = Source(
        url=None, titre="Titre de test", contenu_brut="Contenu de test.", statut=statut
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    source_id = source.id
    db.close()
    return source_id


def test_qualifier_auto_nominal(client, test_db, monkeypatch):
    """Réponse JSON valide : les trois champs sont extraits, statut avancé."""
    _forcer_provider(monkeypatch, '{"categorie": "pro", "legitimite": 4, "interet": 5}')
    source_id = _creer_source(test_db)

    r = client.post(f"/sources/{source_id}/qualification/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] == "pro"
    assert corps["legitimite"] == 4
    assert corps["interet"] == 5
    assert corps["qualified_by"] == "ai"
    assert corps["provider"] == "_FauxProvider"

    db = test_db()
    source = db.get(Source, source_id)
    assert source.statut == "qualified"
    assert db.query(Qualification).filter_by(source_id=source_id).count() == 1
    db.close()


def test_qualifier_auto_balises_markdown(client, test_db, monkeypatch):
    """Réponse entourée de balises ```json ... ``` : les balises sont retirées avant parsing."""
    _forcer_provider(
        monkeypatch,
        '```json\n{"categorie": "metier", "legitimite": 3, "interet": 2}\n```',
    )
    source_id = _creer_source(test_db)

    r = client.post(f"/sources/{source_id}/qualification/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] == "metier"
    assert corps["legitimite"] == 3
    assert corps["interet"] == 2


def test_qualifier_auto_json_malforme(client, test_db, monkeypatch):
    """Réponse qui n'est pas du JSON : les trois champs reviennent à None, pas de plantage."""
    _forcer_provider(monkeypatch, "ceci n'est pas du JSON")
    source_id = _creer_source(test_db)

    r = client.post(f"/sources/{source_id}/qualification/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] is None
    assert corps["legitimite"] is None
    assert corps["interet"] is None
    assert corps["qualified_by"] == "ai"

    # La Qualification est tout de même créée et le statut avance : la
    # réponse ratée n'empêche pas le workflow d'avancer.
    db = test_db()
    assert db.get(Source, source_id).statut == "qualified"
    db.close()


def test_qualifier_auto_categorie_hors_liste(client, test_db, monkeypatch):
    """Categorie hors des 4 valeurs attendues : categorie None, le reste conservé."""
    _forcer_provider(
        monkeypatch, '{"categorie": "inconnue", "legitimite": 3, "interet": 3}'
    )
    source_id = _creer_source(test_db)

    r = client.post(f"/sources/{source_id}/qualification/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] is None
    assert corps["legitimite"] == 3
    assert corps["interet"] == 3


def test_qualifier_auto_notes_hors_bornes(client, test_db, monkeypatch):
    """Notes hors 1-5 : legitimite/interet None, categorie conservée."""
    _forcer_provider(
        monkeypatch, '{"categorie": "perso", "legitimite": 12, "interet": 0}'
    )
    source_id = _creer_source(test_db)

    r = client.post(f"/sources/{source_id}/qualification/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] == "perso"
    assert corps["legitimite"] is None
    assert corps["interet"] is None


def test_qualifier_auto_champ_manquant(client, test_db, monkeypatch):
    """Champs absents du JSON (pas juste vides) : reviennent à None sans planter."""
    _forcer_provider(monkeypatch, '{"categorie": "pro"}')
    source_id = _creer_source(test_db)

    r = client.post(f"/sources/{source_id}/qualification/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["categorie"] == "pro"
    assert corps["legitimite"] is None
    assert corps["interet"] is None


def test_qualifier_auto_source_introuvable(client):
    r = client.post("/sources/999999/qualification/auto")

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"
