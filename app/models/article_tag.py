"""Modèle ``ArticleTag`` : association explicite Article <-> Tag.

Table d'association à part entière (pas un ``secondary=`` implicite) car elle
porte une métadonnée : ``added_by`` (tag posé par l'IA ou ajouté à la main).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base, utcnow

# Origine de l'ajout du tag sur l'article.
ADDED_BY = ("ai", "manual")


class ArticleTag(Base):
    __tablename__ = "article_tags"
    __table_args__ = (
        # Un même tag ne peut être associé qu'une seule fois au même article.
        UniqueConstraint("article_id", "tag_id", name="uq_article_tag"),
    )

    id = Column(Integer, primary_key=True)

    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    added_by = Column(String(10), nullable=False)

    # Pas d'``updated_at`` : un lien article-tag se crée ou se supprime,
    # il ne se modifie pas.
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    article = relationship("Article", back_populates="article_tags")
    tag = relationship("Tag", back_populates="article_tags")

    def __repr__(self) -> str:
        return f"<ArticleTag id={self.id} article_id={self.article_id} tag_id={self.tag_id}>"
