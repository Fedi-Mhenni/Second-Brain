"""Modèle ``Qualification`` : évaluation d'une Source à l'étape « Qualifier ».

Relation 1-1 avec Source. Alimentée soit par l'IA soit manuellement
(``qualified_by``) ; validation du champ ``categorie`` faite en couche
service (pas dans le modèle), même logique que ``Source.STATUTS``.
"""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base, utcnow

# Les quatre catégories possibles. Référence pour la validation en service.
CATEGORIES = ("metier", "pro", "perso", "culture")

# Origine de la qualification : IA ou saisie manuelle.
QUALIFIED_BY = ("ai", "manual")


class Qualification(Base):
    __tablename__ = "qualifications"
    __table_args__ = (
        # Champs remplis par l'IA : on borne en base pour ne jamais accepter
        # une valeur hors échelle, même en cas de bug côté appelant.
        CheckConstraint(
            "legitimite IS NULL OR legitimite BETWEEN 1 AND 5",
            name="ck_qualification_legitimite_range",
        ),
        CheckConstraint(
            "interet IS NULL OR interet BETWEEN 1 AND 5",
            name="ck_qualification_interet_range",
        ),
    )

    id = Column(Integer, primary_key=True)

    # Une Source a au plus une Qualification -> relation un-à-un.
    source_id = Column(
        Integer,
        ForeignKey("sources.id"),
        unique=True,
        nullable=False,
    )

    categorie = Column(String(20), nullable=True)

    # Échelle 1 à 5 (voir CheckConstraint ci-dessus).
    legitimite = Column(Integer, nullable=True)
    interet = Column(Integer, nullable=True)

    qualified_by = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    source = relationship("Source", back_populates="qualification")

    def __repr__(self) -> str:
        return f"<Qualification id={self.id} source_id={self.source_id} categorie={self.categorie!r}>"
