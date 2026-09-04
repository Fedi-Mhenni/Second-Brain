"""Routes HTML server-rendered : dashboard, formulaire de capture, liste des sources.

Ces routes ne portent aucune logique métier : elles appellent les services
existants (``app.services.capture``), puis rendent un template ou
redirigent. L'API JSON de ``app/routes/capture.py`` reste inchangée — ces
routes web vivent sur des chemins distincts (``POST /capture`` ici, contre
``POST /capture/url`` et ``POST /capture/note`` côté API JSON).
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
    """Récupère l'instance Jinja2Templates configurée dans ``app/main.py``."""
    return request.app.state.templates


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    total = db.query(Source).count()
    return _templates(request).TemplateResponse(
        request, "dashboard.html", {"total": total}
    )


@router.get("/sources")
def liste_sources(request: Request, db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.created_at.desc()).all()
    return _templates(request).TemplateResponse(
        request, "sources.html", {"sources": sources}
    )


@router.get("/capture")
def formulaire_capture(request: Request, erreur: str | None = None):
    return _templates(request).TemplateResponse(
        request, "capture.html", {"erreur": erreur}
    )


@router.post("/capture")
def soumettre_capture(
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

    return RedirectResponse("/sources", status_code=303)
