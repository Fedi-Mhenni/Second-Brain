"""Tests de ``POST /sources/{id}/digest/auto`` (digestion via LLMProvider).

Le provider est forcé sur ``MockProvider`` par ``monkeypatch`` : les tests
sont déterministes et ne font aucun appel réseau, quelle que soit la config
``.env`` de la machine.
"""

import pytest

from app.models import Source
from app.services.llm_provider import _MOCK_SUFFIXE, MockProvider


@pytest.fixture(autouse=True)
def _force_mock_provider(monkeypatch):
    """Remplace ``get_llm_provider`` (tel qu'importé par le service digerer)."""
    monkeypatch.setattr(
        "app.services.digerer.get_llm_provider", lambda: MockProvider()
    )


def _creer_source(test_db, *, contenu_brut, titre="Titre", statut="captured") -> int:
    db = test_db()
    source = Source(url=None, titre=titre, contenu_brut=contenu_brut, statut=statut)
    db.add(source)
    db.commit()
    db.refresh(source)
    source_id = source.id
    db.close()
    return source_id


def test_digest_auto_ok(client, test_db):
    source_id = _creer_source(
        test_db, contenu_brut="Un contenu brut assez long à résumer automatiquement."
    )

    r = client.post(f"/sources/{source_id}/digest/auto")

    assert r.status_code == 200
    corps = r.json()
    assert corps["provider"] == "MockProvider"
    # Le résumé vient bien du Mock (suffixe reconnaissable), pas d'un vrai appel.
    assert corps["resume"].endswith(_MOCK_SUFFIXE)
    assert corps["source_id"] == source_id

    # L'upsert de l'Article et l'avancement de statut (digestion manuelle réutilisée) ont joué.
    db = test_db()
    source = db.get(Source, source_id)
    assert source.statut == "digested"
    assert source.article is not None
    db.close()


def test_digest_auto_sans_contenu_brut(client, test_db):
    source_id = _creer_source(test_db, contenu_brut=None)

    r = client.post(f"/sources/{source_id}/digest/auto")

    assert r.status_code == 400
    assert r.json()["detail"] == "Aucun contenu à digérer"


def test_digest_auto_contenu_brut_blanc(client, test_db):
    source_id = _creer_source(test_db, contenu_brut="   \n  ")

    r = client.post(f"/sources/{source_id}/digest/auto")

    assert r.status_code == 400


def test_digest_auto_source_introuvable(client):
    r = client.post("/sources/999999/digest/auto")

    assert r.status_code == 404
    assert r.json()["detail"] == "Source introuvable"
