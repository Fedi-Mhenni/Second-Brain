"""Modèle ``Qualification`` : évaluation d'une Source à l'étape « Qualifier ».

Table séparée plutôt que des colonnes ajoutées directement sur ``Source`` :
la qualification est une donnée qui n'existe qu'à partir d'une étape précise
du workflow (elle est vide avant, potentiellement corrigée après), exactement
comme ``Article`` est séparé de ``Source`` pour l'étape Digérer. Ça évite
d'avoir une table ``Source`` qui porte des colonnes vides pendant la majeure
partie de la vie de la ligne, et ça garde une frontière claire : une table
par étape du pipeline.

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
        # legitimite/interet sont remplis par l'IA : on ne contrôle donc pas
        # leur valeur au moment de l'écriture comme on le ferait pour une
        # saisie utilisateur passée par un formulaire. La contrainte vit en
        # base plutôt que dans le seul service appelant pour rester valable
        # quel que soit le point d'entrée qui écrit la ligne (service de
        # qualification futur, script de seed, requête manuelle, bug dans le
        # parsing de la réponse IA) : la base refuse la valeur hors échelle
        # dans tous les cas, elle ne fait pas confiance à l'appelant.
        # ``IS NULL OR`` : indispensable, sinon la contrainte interdirait
        # aussi l'état « pas encore qualifié » (legitimite/interet à NULL).
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
