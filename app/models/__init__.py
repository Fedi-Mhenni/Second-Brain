"""Modèles SQLAlchemy de l'application.

Importer ce paquet enregistre toutes les tables sur ``Base.metadata`` ;
c'est ce dont ``init_db()`` (dans ``app/database.py``) a besoin pour les créer.
"""

from app.models.folder import Folder
from app.models.source import Source
from app.models.article import Article
from app.models.qualification import Qualification
from app.models.tag import Tag
from app.models.article_tag import ArticleTag
from app.models.republication import Republication

__all__ = [
    "Folder",
    "Source",
    "Article",
    "Qualification",
    "Tag",
    "ArticleTag",
    "Republication",
]
