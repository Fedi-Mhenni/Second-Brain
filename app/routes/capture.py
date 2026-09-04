"""Endpoints de l'étape « Capter » : ``POST /capture/url`` et ``POST /capture/note``."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl, StringConstraints
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.capture import UrlDejaCaptee, capture_note, capture_url

# ``prefix`` : toutes les routes de ce fichier commencent par /capture.
# ``tags`` : regroupe ces routes sous « capture » dans la doc /docs.
router = APIRouter(prefix="/capture", tags=["capture"])


class CaptureUrlIn(BaseModel):
    """Corps de la requête : l'URL à capter.

    Le type ``HttpUrl`` fait que FastAPI renvoie une 422 tout seul si l'URL est
    absente ou malformée — on n'a pas à le vérifier nous-mêmes.
    """

    url: HttpUrl


class CaptureUrlOut(BaseModel):
    """Réponse : la Source créée, plus le résultat du fetch."""

    id: int
    url: str
    titre: str | None
    statut: str
    fetched: bool  # True si le contenu de la page a bien été récupéré
    fetch_error: str | None  # code court de l'erreur quand ``fetched`` est False


@router.post(
    "/url",
    response_model=CaptureUrlOut,
    status_code=status.HTTP_201_CREATED,
)
def capture_url_route(payload: CaptureUrlIn, db: Session = Depends(get_db)):
    """Capte une URL : enregistre une ``Source`` au statut ``captured``.

    Le contenu de la page est récupéré au mieux ; si le site est injoignable ou
    trop lent, la Source est quand même créée et ``fetched`` vaut ``false``.
    """
    try:
        # ``str(...)`` : HttpUrl est un objet Pydantic, le service veut une chaîne.
        source, result = capture_url(db, str(payload.url))
    except UrlDejaCaptee as exc:
        # 409 Conflict : la ressource existe déjà.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "URL déjà captée", "id": exc.source_id},
        )

    return CaptureUrlOut(
        id=source.id,
        url=source.url,
        titre=source.titre,
        statut=source.statut,
        fetched=result.ok,
        fetch_error=result.error,
    )


class CaptureNoteIn(BaseModel):
    """Corps de la requête : le texte libre à enregistrer comme note."""

    # ``strip_whitespace`` + ``min_length=1`` : un texte vide ou fait uniquement
    # d'espaces est refusé par FastAPI (422), on n'a pas à le vérifier nous-mêmes.
    texte: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CaptureNoteOut(BaseModel):
    """Réponse : la Source créée (sans renvoyer le texte complet)."""

    id: int
    titre: str | None
    statut: str


@router.post(
    "/note",
    response_model=CaptureNoteOut,
    status_code=status.HTTP_201_CREATED,
)
def capture_note_route(payload: CaptureNoteIn, db: Session = Depends(get_db)):
    """Capte une note libre : enregistre une ``Source`` au statut ``captured``.

    Aucun accès réseau : le texte est stocké tel quel dans ``contenu_brut`` et le
    ``titre`` est un extrait de ses premiers mots.
    """
    source = capture_note(db, payload.texte)
    return CaptureNoteOut(id=source.id, titre=source.titre, statut=source.statut)
