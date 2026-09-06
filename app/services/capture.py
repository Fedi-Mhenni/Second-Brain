"""Service de l'étape « Capter ».

Deux points d'entrée :
- ``capture_url``  : télécharge une page, en extrait titre + contenu, crée une Source ;
- ``capture_note`` : enregistre directement un texte libre (aucun accès réseau).

Les routes ``POST /api/capture/url`` et ``POST /api/capture/note`` ne font que
valider l'entrée et appeler la fonction correspondante (idem pour le
formulaire HTML de ``app/routes/web.py``, qui appelle ces mêmes fonctions).
"""

from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Source

# En-tête envoyé à chaque requête : certains sites renvoient une erreur ou une
# page vide si le client ne se présente pas comme un navigateur.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SecondBrainBot/0.1)",
}

# Délai maximum (connexion + lecture) avant d'abandonner le fetch.
_TIMEOUT = httpx.Timeout(10.0)

# Longueur maximale de texte conservée : au-delà, ça n'aide pas la qualification
# et ça alourdit la base pour rien.
_MAX_CONTENU = 50_000

# Longueur max du titre dérivé automatiquement du texte d'une note.
_TITRE_MAX = 120


@dataclass
class FetchResult:
    """Résultat d'une tentative de récupération de page.

    ``ok`` indique si le fetch a réussi. En cas d'échec, ``error`` porte un code
    court (``timeout``, ``unreachable``, ``http_404``…) et ``titre`` / ``contenu``
    restent ``None``.
    """

    ok: bool
    titre: str | None = None
    contenu: str | None = None
    error: str | None = None


def fetch_page(url: str) -> FetchResult:
    """Récupère ``url`` et en extrait le titre et le contenu principal.

    Ne lève jamais d'exception : tout problème réseau ou HTTP est converti en
    ``FetchResult(ok=False, error=...)``, à charge de l'appelant de décider quoi
    en faire.
    """
    try:
        # ``follow_redirects=True`` : suit les redirections (ex. http -> https).
        response = httpx.get(
            url,
            headers=_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        # Lève ``httpx.HTTPStatusError`` si le code de réponse est 4xx ou 5xx.
        response.raise_for_status()
    except httpx.TimeoutException:
        return FetchResult(ok=False, error="timeout")
    except httpx.HTTPStatusError as exc:
        # exc.response.status_code = le code renvoyé par le site (404, 500…).
        return FetchResult(ok=False, error=f"http_{exc.response.status_code}")
    except httpx.RequestError:
        # Couvre DNS introuvable, connexion refusée, hôte injoignable…
        return FetchResult(ok=False, error="unreachable")

    titre, contenu = _extraire(response.text)
    return FetchResult(ok=True, titre=titre, contenu=contenu)


def _extraire(html: str) -> tuple[str | None, str | None]:
    """Extrait ``(titre, contenu principal)`` d'un document HTML.

    Extraction volontairement simple : le titre vient de ``<title>`` (sinon du
    premier ``<h1>``) ; le contenu est le texte des ``<p>`` contenus dans le
    premier ``<article>``, sinon ``<main>``, sinon ``<body>``.
    """
    soup = BeautifulSoup(html, "html.parser")

    # On enlève le contenu non pertinent avant toute extraction.
    for balise in soup(["script", "style", "noscript"]):
        balise.decompose()

    # --- Titre ---
    titre = None
    if soup.title:
        titre = soup.title.get_text(strip=True) or None
    if not titre and soup.h1:
        titre = soup.h1.get_text(strip=True) or None

    # --- Contenu principal ---
    # ``or`` en chaîne : on prend le premier bloc trouvé, ``soup`` en dernier recours.
    racine = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphes = [p.get_text(" ", strip=True) for p in racine.find_all("p")]
    # On assemble les paragraphes non vides, puis on tronque.
    contenu = "\n\n".join(p for p in paragraphes if p)[:_MAX_CONTENU] or None

    return titre, contenu


class UrlDejaCaptee(Exception):
    """Levée quand on tente de capter une URL déjà présente en base."""

    def __init__(self, source_id: int):
        self.source_id = source_id
        super().__init__(f"URL déjà captée (source id={source_id})")


def capture_url(db: Session, url: str) -> tuple[Source, FetchResult]:
    """Capte ``url`` : récupère la page au mieux et enregistre une ``Source``.

    La Source est toujours créée avec le statut ``captured``, même si le fetch a
    échoué : dans ce cas ``titre`` et ``contenu_brut`` restent vides et pourront
    être remplis plus tard. Retourne la Source créée et le ``FetchResult`` (pour
    que la route indique au client si le contenu a bien été récupéré).

    Lève ``UrlDejaCaptee`` si l'URL existe déjà (contrainte d'unicité).
    """
    result = fetch_page(url)

    source = Source(
        url=url,
        titre=result.titre,
        contenu_brut=result.contenu,
        statut="captured",
    )
    db.add(source)
    try:
        db.commit()
    except IntegrityError:
        # Seule contrainte pouvant échouer ici : l'unicité de ``url``.
        db.rollback()
        existante = db.query(Source).filter_by(url=url).one()
        raise UrlDejaCaptee(existante.id)

    db.refresh(source)
    return source, result


def _titre_depuis_texte(texte: str) -> str | None:
    """Fabrique un titre lisible à partir du texte d'une note.

    Normalise les espaces (les sauts de ligne deviennent des espaces) et garde
    les ``_TITRE_MAX`` premiers caractères, avec « … » si le texte était plus long.
    """
    resume = " ".join(texte.split())
    if not resume:
        return None
    if len(resume) <= _TITRE_MAX:
        return resume
    return resume[:_TITRE_MAX].rstrip() + "…"


def capture_note(db: Session, texte: str) -> Source:
    """Capte une note libre : enregistre une ``Source`` sans URL ni fetch.

    ``contenu_brut`` reçoit le texte tel quel (après ``strip``), ``titre`` un
    extrait de ses premiers mots, ``statut`` vaut ``captured``. Retourne la Source.
    """
    texte = texte.strip()
    source = Source(
        url=None,
        titre=_titre_depuis_texte(texte),
        contenu_brut=texte,
        statut="captured",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
