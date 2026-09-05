"""Endpoint de listing : ``GET /sources``."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.sources import lister_sources

router = APIRouter(prefix="/sources", tags=["sources"])


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
