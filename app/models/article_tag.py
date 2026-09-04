"""Modèle ``ArticleTag`` : association explicite Article <-> Tag.

Pourquoi une classe mappée et pas un ``secondary=`` (many-to-many implicite
de SQLAlchemy) : le ``secondary=`` gère lui-même la table intermédiaire, mais
elle ne peut alors porter que les deux clés étrangères — aucune colonne
supplémentaire n'est accessible depuis l'ORM. Ici on a besoin de stocker
``added_by`` sur le lien lui-même (pas sur Article, pas sur Tag : c'est une
propriété de l'association « cet article a ce tag », pas de l'un ou l'autre).
Le pattern « association object » (une vraie classe, comme ici) est la
solution standard de SQLAlchemy dès qu'un lien many-to-many doit porter une
donnée propre.

``added_by`` sert à distinguer un tag posé automatiquement par l'IA (étape
Digérer/Qualifier) d'un tag ajouté ou confirmé à la main : utile pour, plus
tard, permettre à l'utilisateur de revoir/valider les tags proposés par l'IA
sans les confondre avec ses propres choix.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base, utcnow

# Origine de l'ajout du tag sur l'article.
ADDED_BY = ("ai", "manual")


class ArticleTag(Base):
    __tablename__ = "article_tags"
    __table_args__ = (
        # Empêche un doublon exact du même lien (ex. l'IA qui re-suggère un
        # tag déjà ajouté manuellement sur cet article) : la paire
        # (article_id, tag_id) doit rester unique, indépendamment de qui l'a
        # posée en premier.
        UniqueConstraint("article_id", "tag_id", name="uq_article_tag"),
    )

    id = Column(Integer, primary_key=True)

    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    # Voir docstring du module : IA ou ajout manuel, pour pouvoir un jour
    # traiter différemment les tags suggérés des tags confirmés.
    added_by = Column(String(10), nullable=False)

    # Pas d'``updated_at`` : contrairement à Qualification ou Republication,
    # un lien article-tag n'a pas d'état intermédiaire à faire évoluer — il
    # existe ou n'existe pas. Le faire évoluer n'aurait pas de sens métier
    # (on supprime le lien et on en recrée un si besoin), donc pas de colonne
    # qui laisserait croire le contraire.
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    article = relationship("Article", back_populates="article_tags")
    tag = relationship("Tag", back_populates="article_tags")

    def __repr__(self) -> str:
        return f"<ArticleTag id={self.id} article_id={self.article_id} tag_id={self.tag_id}>"
