"""Modèle ``Tag`` : étiquette libre applicable aux Articles.

Table indépendante (pas de colonne "tags" sur Article) car un tag est
réutilisable d'un article à l'autre par nature (ex. "IA générative" doit
pouvoir qualifier plusieurs articles) : le many-to-many est donc la seule
modélisation cohérente. Le lien vers Article passe par ``ArticleTag``
(association explicite, voir ce module et son docstring) plutôt que par un
many-to-many implicite, pour pouvoir tracer qui a ajouté chaque tag
(``added_by``).
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base, utcnow


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)

    # ``unique=True`` : jamais deux fois le même tag.
    nom = Column(String(80), unique=True, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    article_tags = relationship("ArticleTag", back_populates="tag")

    def __repr__(self) -> str:
        return f"<Tag id={self.id} nom={self.nom!r}>"
