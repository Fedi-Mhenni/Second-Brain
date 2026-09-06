"""Endpoints « sources » : ``GET /sources`` (listing) et ``PATCH /sources/{id}/folder`` (Ranger)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ranger import FolderIntrouvable, SourceIntrouvable, ranger_source
from app.services.sources import lister_sources

router = APIRouter(prefix="/sources", tags=["sources"])


class RangerSourceIn(BaseModel):
    """Corps de la requête de rangement : le Folder auquel rattacher la Source."""

    folder_id: int


class SourceOut(BaseModel):
    """Une Source telle que renvoyée par l'API (sans son contenu, potentiellement volumineux)."""

    id: int
    url: str | None
    titre: str | None
    statut: str
    folder_id: int | None


@router.get("", response_model=list[SourceOut])
def lister_sources_route(
    # ``Query(default=None, ...)`` : ce sont des paramètres d'URL optionnels
    # (``?statut=...`` et ``?folder_id=...``), pas des paramètres de chemin ni
    # de corps de requête. FastAPI les détecterait comme tels même sans
    # ``Query(...)`` explicite ; on l'utilise ici pour leur ajouter une
    # description visible dans Swagger.
    statut: str | None = Query(
        default=None, description="Filtre par statut (ex. 'captured', 'ranged')"
    ),
    folder_id: int | None = Query(
        default=None, description="Filtre par identifiant de dossier"
    ),
    db: Session = Depends(get_db),
):
    """Liste les Sources, filtrées par statut et/ou dossier si précisé."""
    sources = lister_sources(db, statut=statut, folder_id=folder_id)
    # Construction explicite de chaque SourceOut depuis l'objet ORM, comme
    # pour Folder dans app/routes/folders.py (même convention dans le projet).
    return [
        SourceOut(
            id=s.id, url=s.url, titre=s.titre, statut=s.statut, folder_id=s.folder_id
        )
        for s in sources
    ]


@router.patch(
    "/{source_id}/folder",
    response_model=SourceOut,
    status_code=status.HTTP_200_OK,
)
def ranger_source_route(
    source_id: int, payload: RangerSourceIn, db: Session = Depends(get_db)
):
    """Range une Source existante dans un Folder existant.

    Le statut passe à ``"ranged"`` seulement si la Source n'a pas déjà
    dépassé cette étape du workflow (voir ``app.services.ranger``).
    """
    try:
        source = ranger_source(db, source_id, payload.folder_id)
    except SourceIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable"
        )
    except FolderIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder introuvable"
        )

    return SourceOut(
        id=source.id,
        url=source.url,
        titre=source.titre,
        statut=source.statut,
        folder_id=source.folder_id,
    )
