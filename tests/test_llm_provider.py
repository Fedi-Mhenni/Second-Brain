"""Tests de ``MockProvider`` et de ``get_llm_provider`` (aucune fixture, tests purs)."""

from app.services.llm_provider import LLMProvider, MockProvider, get_llm_provider

_TITRE = "Un titre d'exemple"
_CONTENU = (
    "Ceci est un contenu d'article assez long pour dépasser les cent premiers "
    "caractères repris tels quels par le MockProvider, et vérifier le reste."
)


def test_resume_non_vide():
    resume = MockProvider().resumer(_TITRE, _CONTENU)
    assert resume != ""


def test_resume_est_une_chaine():
    resume = MockProvider().resumer(_TITRE, _CONTENU)
    assert isinstance(resume, str)


def test_resume_non_vide_meme_sur_contenu_vide():
    # Contenu vide : la sortie se réduit au suffixe, donc reste non vide.
    resume = MockProvider().resumer(_TITRE, "")
    assert isinstance(resume, str)
    assert resume != ""


def test_resume_deterministe():
    provider = MockProvider()
    premier = provider.resumer(_TITRE, _CONTENU)
    second = provider.resumer(_TITRE, _CONTENU)
    assert premier == second


def test_get_llm_provider_renvoie_un_llm_provider():
    provider = get_llm_provider()
    # Instance d'une sous-classe concrète de l'interface abstraite.
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, MockProvider)
