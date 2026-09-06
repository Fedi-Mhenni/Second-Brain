"""Abstraction ``LLMProvider`` : point d'entrée unique pour résumer un texte.

Prévue au cadrage : aucune route ni service métier n'appelle un LLM directement,
tout passe par cette interface.

- ``LLMProvider`` : l'interface (classe abstraite).
- ``MockProvider`` : résumé bidon déterministe, aucun réseau (dev / tests).
- ``GeminiProvider`` : vrai appel HTTP à l'API Google Gemini, avec repli
  automatique sur ``MockProvider`` si l'appel échoue pour n'importe quelle raison.
- ``get_llm_provider()`` : choisit l'implémentation selon la config.
"""

import os
from abc import ABC, abstractmethod

import httpx
from dotenv import load_dotenv

# Charge les variables de .env dans l'environnement (idempotent : sans effet si
# déjà fait ailleurs, ex. app/database.py).
load_dotenv()

# --- Réglages MockProvider ---------------------------------------------------

# Longueur de l'extrait repris tel quel par le MockProvider.
_MOCK_EXTRAIT = 100

# Suffixe ajouté par le MockProvider : permet de repérer un résumé « bidon »
# à l'œil nu (dans les tests, dans l'app pendant le dev).
_MOCK_SUFFIXE = " [résumé généré par MockProvider]"

# --- Réglages GeminiProvider ----------------------------------------------------

# Modèle Gemini utilisé (rapide et économique, adapté au résumé). Une seule
# ligne à changer si on veut un autre modèle.
_GEMINI_MODEL = "gemini-3.6-flash"

# Endpoint REST « generateContent » de l'API Gemini v1beta.
_GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_GEMINI_MODEL}:generateContent"
)

# Délai max (connexion + lecture) : une génération est plus lente qu'un GET.
_GEMINI_TIMEOUT = httpx.Timeout(20.0)


class LLMProvider(ABC):
    """Interface d'un fournisseur de résumé.

    ``ABC`` = *Abstract Base Class* : cette classe ne peut pas être instanciée
    directement (``LLMProvider()`` lève ``TypeError``). Elle sert seulement de
    contrat : toute sous-classe concrète doit fournir sa propre ``resumer``.
    """

    @abstractmethod
    def resumer(self, titre: str, contenu: str) -> str:
        """Retourne un résumé de ``contenu`` (``titre`` sert de contexte).

        ``@abstractmethod`` : une sous-classe qui n'implémente pas cette méthode
        reste abstraite et ne peut pas être instanciée non plus. Il n'y a pas de
        corps utile ici, d'où le simple ``...``.
        """
        ...


class MockProvider(LLMProvider):
    """Fournisseur de test : résumé bidon mais déterministe, aucun appel réseau.

    Utilisé pour développer et tester le reste de l'application sans dépendre
    d'une clé d'API ni d'un service externe.
    """

    def resumer(self, titre: str, contenu: str) -> str:
        # On reprend les 100 premiers caractères du contenu et on ajoute un
        # suffixe reconnaissable. Même entrée -> même sortie (déterministe).
        # ``contenu[:100]`` sur une chaîne courte ou vide renvoie ce qu'il y a
        # (voire ""), donc la sortie n'est jamais vide grâce au suffixe.
        return contenu[:_MOCK_EXTRAIT] + _MOCK_SUFFIXE


class GeminiProvider(LLMProvider):
    """Fournisseur réel : appelle l'API Gemini en HTTP direct (httpx, pas de SDK).

    ``resumer`` ne lève jamais : toute erreur (pas de clé, réseau, timeout,
    HTTP 4xx/5xx, JSON inattendu) fait retomber sur ``MockProvider``.
    """

    def __init__(self) -> None:
        # Lue à la construction. Peut être None ou "" -> traité comme « pas de clé ».
        self._api_key = os.getenv("GEMINI_API_KEY")

    def _construire_prompt(self, titre: str, contenu: str) -> str:
        """Assemble l'instruction envoyée au modèle."""
        return (
            "Résume en français, en 3 à 5 phrases, l'article suivant. "
            "Réponds uniquement par le résumé, sans introduction.\n\n"
            f"Titre : {titre}\n\n"
            f"Contenu :\n{contenu}"
        )

    def resumer(self, titre: str, contenu: str) -> str:
        try:
            if not self._api_key:
                # Pas de clé : inutile de tenter l'appel, on force le repli.
                raise RuntimeError("GEMINI_API_KEY non configurée")

            response = httpx.post(
                _GEMINI_URL,
                headers={"x-goog-api-key": self._api_key},
                json={
                    "contents": [
                        {"parts": [{"text": self._construire_prompt(titre, contenu)}]}
                    ]
                },
                timeout=_GEMINI_TIMEOUT,
            )
            # Lève httpx.HTTPStatusError si le code est 4xx/5xx.
            response.raise_for_status()

            # Chemin attendu dans la réponse Gemini : candidates[0].content.parts[0].text
            # Toute clé/indice manquant lève KeyError/IndexError/TypeError, capturé plus bas.
            texte = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            texte = texte.strip()
            if not texte:
                raise ValueError("réponse Gemini vide")
            return texte

        except Exception:
            # ``except Exception`` volontairement large : le contrat de resumer()
            # est « ne jamais lever, toujours renvoyer un résumé exploitable »
            # (exigence de résilience du cadrage — un appel LLM raté ne doit
            # jamais casser le flux applicatif). Dégrader vers MockProvider sur
            # *n'importe quelle* erreur EST le comportement voulu : pas de clé,
            # DNS, timeout, HTTP 4xx/5xx, JSON inattendu... même issue pour tous.
            # C'est différent d'un except nu ailleurs, qui masquerait un vrai bug.
            return MockProvider().resumer(titre, contenu)


def get_llm_provider() -> LLMProvider:
    """Retourne le fournisseur LLM à utiliser, selon la configuration.

    ``GeminiProvider`` si ``GEMINI_API_KEY`` est renseignée dans l'environnement,
    sinon ``MockProvider`` directement (inutile de tenter un appel voué à l'échec).
    """
    if os.getenv("GEMINI_API_KEY"):
        return GeminiProvider()
    return MockProvider()
