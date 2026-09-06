"""Abstraction ``LLMProvider`` : point d'entrée unique pour résumer un texte.

Prévue au cadrage : aucune route ni service métier n'appelle un LLM directement,
tout passe par cette interface. On pose ici l'interface + une implémentation
``MockProvider`` (sans réseau, pour développer et tester). ``GeminiProvider``
(vrai appel HTTP) viendra dans une brique séparée, une fois le Mock validé.
"""

from abc import ABC, abstractmethod

# Longueur de l'extrait repris tel quel par le MockProvider.
_MOCK_EXTRAIT = 100

# Suffixe ajouté par le MockProvider : permet de repérer un résumé « bidon »
# à l'œil nu (dans les tests, dans l'app pendant le dev).
_MOCK_SUFFIXE = " [résumé généré par MockProvider]"


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


def get_llm_provider() -> LLMProvider:
    """Retourne le fournisseur LLM à utiliser.

    Pour l'instant toujours un ``MockProvider``. Quand ``GeminiProvider`` existera,
    c'est ici (et seulement ici) qu'on choisira l'un ou l'autre, selon la config.
    """
    return MockProvider()
