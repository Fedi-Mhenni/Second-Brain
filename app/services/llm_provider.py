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

from app.config import PROFIL_VEILLE

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

    @abstractmethod
    def generer(self, prompt: str) -> str:
        """Retourne la réponse brute du modèle pour ``prompt``, envoyé tel quel.

        Contrairement à ``resumer``, qui construit lui-même son prompt de
        résumé, cette méthode sert les usages où l'appelant a besoin de
        contrôler le prompt exact (ex. demander une réponse JSON stricte
        pour la qualification, voir ``app.services.qualifier``).
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

    def generer(self, prompt: str) -> str:
        # Même logique que ``resumer`` : déterministe, aucun réseau. Ce n'est
        # volontairement pas du JSON valide, même si l'appelant en demande un
        # (ex. app.services.qualifier) : ça exerce réellement le chemin de
        # repli défensif de l'appelant plutôt que de le contourner en lui
        # fournissant une réponse toute faite.
        return prompt[:_MOCK_EXTRAIT] + _MOCK_SUFFIXE


class GeminiProvider(LLMProvider):
    """Fournisseur réel : appelle l'API Gemini en HTTP direct (httpx, pas de SDK).

    ``resumer`` ne lève jamais : toute erreur (pas de clé, réseau, timeout,
    HTTP 4xx/5xx, JSON inattendu) fait retomber sur ``MockProvider``.
    """

    def __init__(self) -> None:
        # Lue à la construction. Peut être None ou "" -> traité comme « pas de clé ».
        self._api_key = os.getenv("GEMINI_API_KEY")

    def _construire_prompt(self, titre: str, contenu: str) -> str:
        """Assemble l'instruction envoyée au modèle.

        La 1re ligne injecte ``PROFIL_VEILLE`` (app/config.py) : elle oriente le
        ton et les angles selon le profil de l'instance, sans toucher aux faits.
        Le reste (format « 3 à 5 phrases en français ») est inchangé.
        """
        return (
            f"Tu résumes pour {PROFIL_VEILLE} : adapte les angles et le "
            "vocabulaire à ce profil, sans changer les faits.\n\n"
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

    def generer(self, prompt: str) -> str:
        """Envoie ``prompt`` tel quel à Gemini, sans reconstruire de prompt.

        Même contrat de résilience que ``resumer`` : toute erreur retombe sur
        ``MockProvider.generer``, jamais d'exception qui remonte à l'appelant.
        """
        try:
            if not self._api_key:
                raise RuntimeError("GEMINI_API_KEY non configurée")

            response = httpx.post(
                _GEMINI_URL,
                headers={"x-goog-api-key": self._api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=_GEMINI_TIMEOUT,
            )
            response.raise_for_status()

            texte = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            texte = texte.strip()
            if not texte:
                raise ValueError("réponse Gemini vide")
            return texte

        except Exception:
            # Voir le commentaire équivalent dans ``resumer`` : même contrat.
            return MockProvider().generer(prompt)


def get_llm_provider() -> LLMProvider:
    """Retourne le fournisseur LLM à utiliser, selon la configuration.

    ``GeminiProvider`` si ``GEMINI_API_KEY`` est renseignée dans l'environnement,
    sinon ``MockProvider`` directement (inutile de tenter un appel voué à l'échec).
    """
    if os.getenv("GEMINI_API_KEY"):
        return GeminiProvider()
    return MockProvider()
