"""Tests de POST /capture/url : succès, doublon, échecs réseau, entrée invalide.

Chaque test qui simule un fetch remplace ``httpx.get`` (voir
``_mock_httpx_get``) au lieu d'appeler le vrai réseau : les tests restent
rapides, reproductibles, et ne dépendent pas d'un site externe disponible.
On construit de vrais objets ``httpx.Response`` (pas un mock générique) pour
que ``raise_for_status()`` se comporte exactement comme en production.
"""

import httpx
import pytest

from app.models import Source
from app.services.capture import SchemaUrlNonAutorise, capture_url, fetch_page


def _mock_httpx_get(monkeypatch, *, response=None, exception=None):
    """Remplace ``httpx.get`` par un faux qui renvoie ``response`` ou lève ``exception``.

    ``httpx`` est un module partagé (import mis en cache par Python) : patcher
    son attribut ``get`` ici affecte tout code qui fait ``httpx.get(...)``,
    y compris ``app/services/capture.py``. ``monkeypatch`` restaure l'original
    automatiquement à la fin du test.
    """

    def fake_get(url, **kwargs):
        if exception is not None:
            raise exception
        return response

    monkeypatch.setattr(httpx, "get", fake_get)


def _reponse_html(status_code: int, url: str, html: str = "") -> httpx.Response:
    """Construit une vraie réponse httpx, sans requête réseau."""
    return httpx.Response(status_code, request=httpx.Request("GET", url), text=html)


def test_capture_url_ok(client, test_db, monkeypatch):
    """Capture réussie : la page est récupérée, le titre extrait, la Source enregistrée."""
    url = "https://exemple.test/article"
    html = (
        "<html><head><title>Un super article</title></head>"
        "<body><p>Contenu de l'article.</p></body></html>"
    )
    _mock_httpx_get(monkeypatch, response=_reponse_html(200, url, html))

    r = client.post("/capture/url", json={"url": url})

    assert r.status_code == 201
    corps = r.json()
    assert corps["fetched"] is True
    assert corps["fetch_error"] is None
    assert corps["titre"] == "Un super article"
    assert corps["statut"] == "captured"

    # Vérification directe en base, via la fabrique de sessions de test_db.
    db = test_db()
    assert db.query(Source).count() == 1
    db.close()


def test_capture_url_deja_captee(client, monkeypatch):
    """Une 2e capture de la même URL est refusée (409), la 1re Source n'est pas dupliquée."""
    url = "https://exemple.test/doublon"
    _mock_httpx_get(monkeypatch, response=_reponse_html(200, url, "<title>T</title>"))

    premier = client.post("/capture/url", json={"url": url})
    assert premier.status_code == 201

    deuxieme = client.post("/capture/url", json={"url": url})

    assert deuxieme.status_code == 409
    assert deuxieme.json()["detail"]["id"] == premier.json()["id"]


def test_capture_url_injoignable(client, monkeypatch):
    """Domaine injoignable (DNS, connexion refusée...) : la Source est quand même créée."""
    url = "https://injoignable.test/"
    _mock_httpx_get(monkeypatch, exception=httpx.ConnectError("connexion refusée"))

    r = client.post("/capture/url", json={"url": url})

    assert r.status_code == 201
    corps = r.json()
    assert corps["fetched"] is False
    assert corps["fetch_error"] == "unreachable"
    assert corps["titre"] is None


def test_capture_url_404(client, monkeypatch):
    """Page introuvable (404) : même traitement qu'un site injoignable, code d'erreur différent."""
    url = "https://exemple.test/page-absente"
    _mock_httpx_get(monkeypatch, response=_reponse_html(404, url, "Not Found"))

    r = client.post("/capture/url", json={"url": url})

    assert r.status_code == 201
    corps = r.json()
    assert corps["fetched"] is False
    assert corps["fetch_error"] == "http_404"


def test_capture_url_invalide(client):
    """URL malformée : rejetée par la validation Pydantic, le service n'est jamais appelé."""
    r = client.post("/capture/url", json={"url": "pas-une-url"})

    assert r.status_code == 422


def test_capture_url_schema_javascript_rejete(test_db):
    """Un schéma autre que http/https (ex. javascript:) est rejeté par le
    service lui-même, pas seulement par la validation Pydantic de la route
    JSON : c'est ce qui protège aussi le formulaire HTML, qui ne passe pas
    par ``HttpUrl`` (voir app/routes/web.py).
    """
    db = test_db()
    with pytest.raises(SchemaUrlNonAutorise):
        capture_url(db, "javascript:alert(1)")

    assert db.query(Source).count() == 0
    db.close()


# --- fetch_page : HTTP 200 mais aucun contenu exploitable -----------------------


def test_fetch_page_contenu_vide_malgre_http_200(monkeypatch):
    """Page qui répond 200 mais sans <p> ni meta description : ok reste True,
    contenu est None et contenu_vide passe à True (cas site anti-scraping / JS).
    """
    url = "https://protege.test/article"
    html = "<html><head><title>Titre</title></head><body><div>nav uniquement</div></body></html>"
    _mock_httpx_get(monkeypatch, response=_reponse_html(200, url, html))

    res = fetch_page(url)

    assert res.ok is True
    assert res.error is None
    assert res.contenu is None
    assert res.contenu_vide is True
    assert res.titre == "Titre"


def test_fetch_page_repli_og_description(monkeypatch):
    """Pas de <p> exploitable mais un <meta property="og:description"> :
    on retombe dessus, contenu_vide reste False.
    """
    url = "https://protege.test/og"
    html = (
        "<html><head><title>T</title>"
        '<meta property="og:description" content="Un résumé fourni par la page.">'
        "</head><body><div></div></body></html>"
    )
    _mock_httpx_get(monkeypatch, response=_reponse_html(200, url, html))

    res = fetch_page(url)

    assert res.ok is True
    assert res.contenu == "Un résumé fourni par la page."
    assert res.contenu_vide is False


def test_fetch_page_repli_meta_description(monkeypatch):
    """Repli secondaire sur <meta name="description"> quand og:description manque."""
    url = "https://protege.test/desc"
    html = (
        "<html><head><title>T</title>"
        '<meta name="description" content="Description meta classique.">'
        "</head><body><p>   </p></body></html>"
    )
    _mock_httpx_get(monkeypatch, response=_reponse_html(200, url, html))

    res = fetch_page(url)

    assert res.contenu == "Description meta classique."
    assert res.contenu_vide is False
