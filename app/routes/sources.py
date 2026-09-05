"""Endpoint de l'étape « Ranger » : ``PATCH /sources/{source_id}/folder``."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ranger import FolderIntrouvable, SourceIntrouvable, ranger_source

router = APIRouter(prefix="/sources", tags=["sources"])


class RangerSourceIn(BaseModel):
    """Corps de la requête : le Folder auquel rattacher la Source."""

    folder_id: int


class SourceOut(BaseModel):
    """Réponse : la Source à jour (sans son contenu, potentiellement volumineux)."""

    id: int
    url: str | None
    titre: str | None
    statut: str
    folder_id: int | None


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
