"""Modèle ``Folder`` : un dossier thématique personnel où l'on range les Sources.

Ensemble volontairement restreint, propre à chaque instance (valeurs de base dans
``scripts/seed.py``). Ranger une Source revient à lui affecter un ``folder_id``.
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base, utcnow


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True)

    # Libellé du dossier. ``unique=True`` : jamais deux dossiers du même nom
    # (c'est aussi ce qui garantit que le seed ne crée pas de doublon).
    nom = Column(String(120), unique=True, nullable=False)

    # Description libre, facultative.
    description = Column(String(500), nullable=True)

    # Suivi temporel, même logique que Source / Article (colonnes avec fuseau).
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Un dossier contient plusieurs Sources. ``back_populates`` tient les deux
    # côtés synchronisés (voir ``Source.folder``) ; la chaîne "Source" évite
    # d'importer la classe ici.
    sources = relationship("Source", back_populates="folder")

    def __repr__(self) -> str:
        return f"<Folder id={self.id} nom={self.nom!r}>"
