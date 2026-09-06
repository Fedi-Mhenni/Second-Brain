"""Service de l'étape « Republier ».

Crée un nouveau brouillon de Republication pour un Article existant. Pas
d'upsert ici (contrairement à Qualifier/Ranger) : voir
``app.models.republication`` — l'absence de contrainte d'unicité sur
``article_id`` est volontaire, un même Article peut être republié plusieurs
fois (canaux ou postures différents), donc chaque appel crée une ligne.
"""

from sqlalchemy.orm import Session

from app.models import Article, Republication


class ArticleIntrouvable(Exception):
    """Levée quand l'Article demandé n'existe pas."""

    def __init__(self, article_id: int):
        self.article_id = article_id
        super().__init__(f"Article introuvable (id={article_id})")


def republier_article(
    db: Session,
    article_id: int,
    canal: str,
    brouillon: str,
    posture: str,
) -> Republication:
    """Crée une nouvelle Republication liée à ``article_id``.

    Lève ``ArticleIntrouvable`` si l'Article n'existe pas.
    """
    article = db.get(Article, article_id)
    if article is None:
        raise ArticleIntrouvable(article_id)

    republication = Republication(
        article_id=article_id,
        canal=canal,
        brouillon=brouillon,
        posture=posture,
    )
    db.add(republication)
    db.commit()
    db.refresh(republication)
    return republication
