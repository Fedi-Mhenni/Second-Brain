"""Modèle ``Article`` : le contenu retravaillé issu d'une ``Source``.

L'Article porte la version lisible/enrichie du contenu et le résumé produit à
l'étape Digérer. Il est lié à une seule Source (relation un-à-un).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base, utcnow


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)

    # Lien vers la Source d'origine.
    # ``ForeignKey("sources.id")`` : contrainte de clé étrangère vers la table ``sources``.
    # ``unique=True``   : une Source donne au plus un Article -> relation un-à-un.
    # ``nullable=False`` : un Article existe toujours à partir d'une Source.
    source_id = Column(
        Integer,
        ForeignKey("sources.id"),
        unique=True,
        nullable=False,
    )

    # Titre nettoyé / réécrit (peut différer du titre brut de la Source).
    titre = Column(String(512), nullable=True)

    # Version travaillée et lisible du contenu (par opposition à ``Source.contenu_brut``).
    contenu = Column(Text, nullable=True)

    # Résumé produit à l'étape Digérer.
    resume = Column(Text, nullable=True)

    # Suivi temporel (même logique que sur Source, colonnes avec fuseau).
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Accès inverse : depuis un Article, ``article.source`` renvoie la Source liée.
    source = relationship("Source", back_populates="article")

    # Tags de l'article, via l'association explicite ArticleTag (porte
    # ``added_by``, voir ce modèle) -> pas de relation many-to-many directe
    # vers Tag, sinon l'ORM ne donnerait plus accès à cette métadonnée.
    # Le rangement par tags porte sur l'Article (contenu retravaillé), pas
    # sur la Source brute : on tague ce qui a été digéré, pas la page brute.
    article_tags = relationship("ArticleTag", back_populates="article")

    # Une Republication ne peut exister qu'à partir d'un Article (donc
    # seulement après digestion) : voir la docstring de Republication pour
    # la raison de ce rattachement (contrainte d'ordre du workflow portée
    # par le schéma). Un Article peut donner lieu à plusieurs Republications
    # (canaux/postures différents) -> relation un-à-plusieurs, pas de
    # ``uselist=False``.
    republications = relationship("Republication", back_populates="article")

    def __repr__(self) -> str:
        return f"<Article id={self.id} source_id={self.source_id}>"
