"""Tests de ``MockProvider``, ``GeminiProvider`` et ``get_llm_provider``.

Aucun test ne fait de vrai appel réseau : ``httpx.post`` est remplacé par
``monkeypatch`` (comme ``httpx.get`` dans ``tests/test_capture.py``).
"""

import httpx

from app.services.llm_provider import (
    GeminiProvider,
    LLMProvider,
    MockProvider,
    _MOCK_SUFFIXE,
    get_llm_provider,
)

_TITRE = "Un titre d'exemple"
_CONTENU = (
    "Ceci est un contenu d'article assez long pour dépasser les cent premiers "
    "caractères repris tels quels par le MockProvider, et vérifier le reste."
)


def _mock_httpx_post(monkeypatch, *, response=None, exception=None):
    """Remplace ``httpx.post`` par un faux qui renvoie ``response`` ou lève ``exception``."""

    def fake_post(url, **kwargs):
        if exception is not None:
            raise exception
        return response

    monkeypatch.setattr(httpx, "post", fake_post)


def _reponse_gemini(texte: str, status_code: int = 200) -> httpx.Response:
    """Construit une vraie réponse httpx au format Gemini, sans requête réseau."""
    return httpx.Response(
        status_code,
        request=httpx.Request("POST", "https://gemini.test/"),
        json={"candidates": [{"content": {"parts": [{"text": texte}]}}]},
    )


# --- MockProvider ------------------------------------------------------------


def test_mock_resume_non_vide():
    assert MockProvider().resumer(_TITRE, _CONTENU) != ""


def test_mock_resume_est_une_chaine():
    assert isinstance(MockProvider().resumer(_TITRE, _CONTENU), str)


def test_mock_resume_non_vide_meme_sur_contenu_vide():
    resume = MockProvider().resumer(_TITRE, "")
    assert isinstance(resume, str) and resume != ""


def test_mock_resume_deterministe():
    provider = MockProvider()
    assert provider.resumer(_TITRE, _CONTENU) == provider.resumer(_TITRE, _CONTENU)


# --- GeminiProvider : cas nominal ------------------------------------------------


def test_gemini_reponse_valide(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    _mock_httpx_post(monkeypatch, response=_reponse_gemini("Voici un vrai résumé."))

    resume = GeminiProvider().resumer(_TITRE, _CONTENU)

    # Le vrai texte est renvoyé (pas le repli Mock).
    assert resume == "Voici un vrai résumé."
    assert _MOCK_SUFFIXE not in resume


# --- GeminiProvider : tous les chemins d'échec -> repli MockProvider ------------


def _assert_repli_mock(resume: str):
    """Contrôles communs : jamais vide, toujours str, c'est bien le résultat Mock."""
    assert isinstance(resume, str)
    assert resume != ""
    assert resume.endswith(_MOCK_SUFFIXE)


def test_gemini_timeout_repli_mock(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    _mock_httpx_post(monkeypatch, exception=httpx.TimeoutException("timeout"))

    _assert_repli_mock(GeminiProvider().resumer(_TITRE, _CONTENU))


def test_gemini_erreur_reseau_repli_mock(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    _mock_httpx_post(monkeypatch, exception=httpx.ConnectError("connexion refusée"))

    _assert_repli_mock(GeminiProvider().resumer(_TITRE, _CONTENU))


def test_gemini_http_500_repli_mock(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    _mock_httpx_post(monkeypatch, response=_reponse_gemini("peu importe", status_code=500))

    _assert_repli_mock(GeminiProvider().resumer(_TITRE, _CONTENU))


def test_gemini_json_inattendu_repli_mock(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    mauvaise_forme = httpx.Response(
        200, request=httpx.Request("POST", "https://gemini.test/"), json={"autre": "chose"}
    )
    _mock_httpx_post(monkeypatch, response=mauvaise_forme)

    _assert_repli_mock(GeminiProvider().resumer(_TITRE, _CONTENU))


def test_gemini_sans_cle_repli_mock_sans_appel(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Si un appel HTTP est tenté malgré l'absence de clé, le test échoue.
    def interdit(*args, **kwargs):
        raise AssertionError("httpx.post ne doit pas être appelé sans clé")

    monkeypatch.setattr(httpx, "post", interdit)

    _assert_repli_mock(GeminiProvider().resumer(_TITRE, _CONTENU))


# --- get_llm_provider ------------------------------------------------------------


def test_get_llm_provider_avec_cle(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    assert isinstance(get_llm_provider(), GeminiProvider)


def test_get_llm_provider_sans_cle(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = get_llm_provider()
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, MockProvider)


# --- _construire_prompt : injection du profil de veille ------------------------


def test_prompt_contient_le_profil_veille(monkeypatch):
    """Le PROFIL_VEILLE de l'instance doit apparaître dans le prompt envoyé à Gemini."""
    monkeypatch.setattr(
        "app.services.llm_provider.PROFIL_VEILLE",
        "un trader qui suit la régulation crypto",
    )

    prompt = GeminiProvider()._construire_prompt(_TITRE, _CONTENU)

    assert "un trader qui suit la régulation crypto" in prompt
    assert "sans changer les faits" in prompt


def test_prompt_garde_le_format_3_a_5_phrases(monkeypatch):
    """L'injection du profil ne doit pas casser la consigne de format existante."""
    prompt = GeminiProvider()._construire_prompt(_TITRE, _CONTENU)

    assert "en 3 à 5 phrases" in prompt
    assert f"Titre : {_TITRE}" in prompt
    assert _CONTENU in prompt
