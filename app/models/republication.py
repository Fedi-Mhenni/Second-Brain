"""Modèle ``Republication`` : brouillon de republication d'une Source.

Une Source peut donner lieu à plusieurs Republications (canaux et postures
différents). La republication reste toujours un brouillon éditable : aucune
publication automatique (décision actée, voir docs/CADRAGE.md).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base, utcnow

# Canal de republication visé.
CANAUX = ("linkedin", "x")

# Avancement de la republication.
STATUTS = ("draft", "published")

# Angle éditorial adopté.
POSTURES = ("personal_branding", "entreprise")


class Republication(Base):
    __tablename__ = "republications"

    id = Column(Integer, primary_key=True)

    # Une Source peut avoir plusieurs Republications -> pas d'unicité ici.
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    canal = Column(String(20), nullable=True)

    # Contenu du brouillon, toujours éditable avant copier/coller manuel.
    brouillon = Column(Text, nullable=True)

    statut = Column(String(20), nullable=False, default="draft")

    posture = Column(String(30), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    source = relationship("Source", back_populates="republications")

    def __repr__(self) -> str:
        return (
            f"<Republication id={self.id} source_id={self.source_id} "
            f"canal={self.canal!r} statut={self.statut!r}>"
        )
