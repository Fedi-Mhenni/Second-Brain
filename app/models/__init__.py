"""Modèles SQLAlchemy de l'application.

Importer ce paquet enregistre toutes les tables sur ``Base.metadata`` ;
c'est ce dont ``init_db()`` (dans ``app/database.py``) a besoin pour les créer.
"""

from app.models.source import Source
from app.models.article import Article

__all__ = ["Source", "Article"]
