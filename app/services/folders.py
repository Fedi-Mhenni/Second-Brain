"""Service de listing des Folders."""

from sqlalchemy.orm import Session

from app.models import Folder


def lister_folders(db: Session) -> list[Folder]:
    """Renvoie tous les Folders, triés par nom (ordre alphabétique)."""
    # ``order_by(Folder.nom)`` : le tri est fait par la base de données
    # (une clause SQL ORDER BY), pas en Python après coup sur la liste.
    return db.query(Folder).order_by(Folder.nom).all()
