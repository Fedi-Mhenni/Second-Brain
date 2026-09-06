"""Vérifie que GEMINI_API_KEY permet un vrai appel à l'API Gemini.

N'utilise volontairement pas GeminiProvider : celui-ci retombe
automatiquement sur MockProvider en cas d'échec (voir
app/services/llm_provider.py), ce qui masquerait justement une clé absente
ou invalide derrière un succès silencieux.

Deux appels :
1. ``GET /v1beta/models`` — liste les modèles accessibles avec cette clé.
   Sert aussi de test de connectivité/authentification indépendant du choix
   d'un modèle précis.
2. ``POST /v1beta/models/{modele}:generateContent`` — le même appel que
   GeminiProvider (même URL, même modèle ``_MODELE``, voir
   app/services/llm_provider.py), pour reproduire exactement son échec.

Sur une erreur HTTP, affiche le code ET le corps complet de la réponse :
c'est ce corps qui contient la cause précise côté Google (API non activée,
clé restreinte, quota...). La clé elle-même n'est jamais affichée, dans
aucun message, aucun corps de requête loggé.

Lancement : python -m scripts.verifier_gemini
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv

# Mêmes valeurs que app/services/llm_provider.py (_GEMINI_MODEL / _GEMINI_URL) :
# on veut reproduire exactement l'appel de GeminiProvider, pas une variante.
_MODELE = "gemini-3.6-flash"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_URL_GENERATE = f"{_BASE_URL}/models/{_MODELE}:generateContent"
_URL_MODELS = f"{_BASE_URL}/models"
_TIMEOUT = httpx.Timeout(20.0)


def _afficher_erreur_http(reponse: httpx.Response) -> None:
    """Affiche code + corps complet d'une réponse en erreur (jamais la clé)."""
    print(f"  HTTP {reponse.status_code}")
    try:
        corps = reponse.json()
        print(json.dumps(corps, indent=2, ensure_ascii=False))
    except ValueError:
        print(reponse.text)


def lister_modeles(cle: str) -> list[str] | None:
    """Liste les noms de modèles accessibles avec ``cle``. None si l'appel échoue."""
    print("--- GET /v1beta/models ---")
    try:
        reponse = httpx.get(
            _URL_MODELS, headers={"x-goog-api-key": cle}, timeout=_TIMEOUT
        )
    except httpx.RequestError as exc:
        print(f"  ÉCHEC réseau : {type(exc).__name__}")
        return None

    if reponse.status_code != 200:
        _afficher_erreur_http(reponse)
        return None

    noms = [m.get("name", "?") for m in reponse.json().get("models", [])]
    print(f"  {len(noms)} modèle(s) accessible(s) avec cette clé :")
    for nom in noms:
        print(f"    - {nom}")
    return noms


def tester_generate_content(cle: str) -> bool:
    """Reproduit l'appel exact de GeminiProvider.resumer(). True si succès."""
    print(f"--- POST /v1beta/models/{_MODELE}:generateContent ---")
    try:
        reponse = httpx.post(
            _URL_GENERATE,
            headers={"x-goog-api-key": cle},
            json={"contents": [{"parts": [{"text": "Réponds uniquement par OK."}]}]},
            timeout=_TIMEOUT,
        )
    except httpx.RequestError as exc:
        print(f"  ÉCHEC réseau : {type(exc).__name__}")
        return False

    if reponse.status_code != 200:
        _afficher_erreur_http(reponse)
        return False

    try:
        texte = reponse.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        print("  HTTP 200 mais format de réponse inattendu :")
        print(json.dumps(reponse.json(), indent=2, ensure_ascii=False))
        return False

    print(f"  Réponse du modèle : {texte.strip()!r}")
    return True


def verifier() -> bool:
    load_dotenv()
    cle = os.getenv("GEMINI_API_KEY")

    if not cle:
        print("STATUT : GEMINI_API_KEY absente ou vide -> aucun appel tenté.")
        return False

    noms_modeles = lister_modeles(cle)
    print()
    ok = tester_generate_content(cle)

    print()
    if ok:
        print("STATUT : OK -- la clé est valide, l'appel à Gemini a réussi.")
    else:
        print("STATUT : ÉCHEC -- voir le corps de la réponse ci-dessus pour la cause précise.")
        if noms_modeles is not None and not any(_MODELE in n for n in noms_modeles):
            print(
                f"NOTE : « {_MODELE} » n'apparaît pas dans la liste des modèles "
                "accessibles ci-dessus avec cette clé -- vérifie le nom exact."
            )
    return ok


if __name__ == "__main__":
    sys.exit(0 if verifier() else 1)
