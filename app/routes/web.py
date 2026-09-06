"""Routes HTML server-rendered : dashboard, formulaire de capture, liste des sources.

Pourquoi un fichier séparé de ``app/routes/capture.py`` plutôt que d'ajouter
ces routes au même router : les deux fichiers servent deux contrats et deux
publics différents qui ne doivent pas se contraindre l'un l'autre.
``capture.py`` est une API JSON (corps et réponses typés par des modèles
Pydantic, codes 201/409, pensée pour un client programmatique) ; ce fichier
sert des pages HTML à un navigateur (formulaires ``multipart/form-data``,
réponses de redirection 303). Les mélanger dans un même router obligerait
soit à dupliquer chaque route en deux versions, soit à faire porter à une
seule route la négociation de contenu (JSON vs HTML) — plus complexe pour un
gain nul ici. Les deux fichiers restent alignés parce qu'ils appellent les
mêmes fonctions de service (``app.services.capture``) : la logique de
capture n'existe qu'à un seul endroit, seule la façon de la présenter change.

Ces routes elles-mêmes ne portent aucune logique métier (règle de
CLAUDE.md) : chaque route appelle le service puis rend un template ou
redirige, rien de plus. ``POST /capture`` (ici) et ``POST /capture/url`` /
``POST /capture/note`` (API JSON) sont des chemins distincts par
construction : aucun risque de collision de route entre les deux fichiers.
Idem pour ``GET /liste`` (ici, page HTML de listing) face à ``GET /sources``
(API JSON, ``app/routes/sources.py``) : le coéquipier a tranché que le
contrat JSON garde le chemin d'origine (déjà utilisé par Ranger et Digérer),
c'est donc la page HTML qui porte un nom distinct.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Source
from app.services.capture import UrlDejaCaptee, capture_note, capture_url

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    """Récupère l'instance Jinja2Templates configurée dans ``app/main.py``.

    Passe par ``request.app.state`` plutôt que d'instancier Jinja2Templates
    ici : une seule instance pour toute l'application (voir le commentaire
    dans main.py), et ça évite d'avoir à importer main.py depuis ce module
    alors que main.py importe déjà ce module pour brancher son router.
    """
    return request.app.state.templates


@router.get("/")
def dashboard_route(request: Request, db: Session = Depends(get_db)):
    # Lecture directe sans passer par un service : un comptage brut pour
    # affichage n'est pas une décision métier, juste une projection.
    total = db.query(Source).count()
    return _templates(request).TemplateResponse(
        request, "dashboard.html", {"total": total}
    )


@router.get("/liste")
def liste_sources_route(request: Request, db: Session = Depends(get_db)):
    # Idem : lister/trier pour affichage n'est pas de la logique métier.
    sources = db.query(Source).order_by(Source.created_at.desc()).all()
    return _templates(request).TemplateResponse(
        request, "sources.html", {"sources": sources}
    )


@router.get("/capture")
def formulaire_capture_route(request: Request, erreur: str | None = None):
    return _templates(request).TemplateResponse(
        request, "capture.html", {"erreur": erreur}
    )


@router.post("/capture")
def soumettre_capture_route(
    db: Session = Depends(get_db),
    url: str = Form(default=""),
    texte: str = Form(default=""),
):
    """Traite le formulaire de capture (URL ou note) puis redirige.

    Le formulaire n'envoie qu'un seul des deux champs à la fois (deux
    ``<form>`` distincts dans ``capture.html``) : on regarde lequel est
    renseigné pour choisir le service à appeler.
    """
    if url.strip():
        try:
            capture_url(db, url.strip())
        except UrlDejaCaptee:
            # Cas d'échec géré explicitement : on repasse par le formulaire
            # avec un indicateur d'erreur plutôt que de laisser planter.
            return RedirectResponse("/capture?erreur=deja_captee", status_code=303)
    elif texte.strip():
        capture_note(db, texte.strip())

    return RedirectResponse("/liste", status_code=303)
