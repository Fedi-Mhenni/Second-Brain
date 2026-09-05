"""Endpoint de listing : ``GET /folders``."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.folders import lister_folders

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderOut(BaseModel):
    """Un Folder tel que renvoyé par l'API."""

    id: int
    nom: str
    # ``str | None`` : description est optionnelle sur le modèle (nullable=True).
    description: str | None


@router.get("", response_model=list[FolderOut])
def lister_folders_route(db: Session = Depends(get_db)):
    """Liste tous les Folders existants, triés par nom."""
    folders = lister_folders(db)
    # Construction explicite de chaque FolderOut depuis l'objet ORM, comme
    # pour Source dans app/routes/capture.py (même convention dans le projet).
    return [
        FolderOut(id=f.id, nom=f.nom, description=f.description) for f in folders
    ]
