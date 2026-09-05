"""Modèle ``Republication`` : brouillon de republication d'une Source digérée.

Table séparée de Source (comme Article et Qualification) : republier n'est
pas un état unique mais un ensemble de tentatives indépendantes — le
cadrage demande explicitement de pouvoir republier une même Source sur
plusieurs canaux et dans plusieurs postures (personal branding *et*
entreprise). Une seule ligne par Source ne pourrait pas porter ça ; une table
à part avec ``article_id`` en clé étrangère (non unique) le permet nativement.

Rattachée à ``Article`` plutôt qu'à ``Source`` (retour de review) : le
workflow impose Capter → Qualifier → Ranger → Digérer → Republier, et
Article n'existe qu'une fois la Source digérée (voir app/models/article.py).
En pointant vers Article plutôt que Source, le schéma rend impossible de
créer une Republication avant digestion — la contrainte d'ordre des étapes
est donc portée par la structure de la base (une clé étrangère qui n'existe
pas encore tant que l'Article n'est pas créé), pas par une vérification
ajoutée dans le code applicatif qu'on pourrait oublier ou contourner.

``brouillon`` reste toujours un texte éditable, jamais publié
automatiquement : décision actée du cadrage (délai de validation des API
LinkedIn/X trop long pour le projet) — la vraie publication se fait à la
main, par copier/coller, depuis ce brouillon.
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

    # Volontairement pas ``unique=True`` (contrairement à Article/Qualification) :
    # c'est ce qui permet plusieurs Republications pour un même Article, voir
    # docstring du module. FK vers ``articles.id`` (pas ``sources.id``) : voir
    # docstring du module pour la raison (contrainte d'ordre du workflow).
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)

    canal = Column(String(20), nullable=True)

    # Contenu du brouillon, toujours éditable avant copier/coller manuel.
    brouillon = Column(Text, nullable=True)

    statut = Column(String(20), nullable=False, default="draft")

    posture = Column(String(30), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    article = relationship("Article", back_populates="republications")

    def __repr__(self) -> str:
        return (
            f"<Republication id={self.id} article_id={self.article_id} "
            f"canal={self.canal!r} statut={self.statut!r}>"
        )
