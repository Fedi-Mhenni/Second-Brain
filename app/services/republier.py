"""Service de l'étape « Republier ».

Crée un nouveau brouillon de Republication pour un Article existant. Pas
d'upsert ici (contrairement à Qualifier/Ranger) : voir
``app.models.republication`` — l'absence de contrainte d'unicité sur
``article_id`` est volontaire, un même Article peut être republié plusieurs
fois (canaux ou postures différents), donc chaque appel crée une ligne.
"""

from sqlalchemy.orm import Session

from app.models import Article, Republication
from app.models.source import avancer_statut


class ArticleIntrouvable(Exception):
    """Levée quand l'Article demandé n'existe pas."""

    def __init__(self, article_id: int):
        self.article_id = article_id
        super().__init__(f"Article introuvable (id={article_id})")


class RepublicationIntrouvable(Exception):
    """Levée quand la Republication demandée n'existe pas."""

    def __init__(self, republication_id: int):
        self.republication_id = republication_id
        super().__init__(f"Republication introuvable (id={republication_id})")


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


def publier_republication(db: Session, republication_id: int) -> Republication:
    """Marque une Republication comme publiée et fait avancer sa Source.

    Ne publie rien sur LinkedIn/X (décision actée au cadrage, aucune API
    d'auto-publication) : ce service se contente d'enregistrer que le
    brouillon a été collé et publié à la main. ``republication.article.source``
    traverse les deux relations existantes (Republication -> Article -> Source)
    pour appliquer la même règle d'avancement que Qualifier/Ranger/Digérer
    (voir ``avancer_statut``, app/models/source.py).

    Lève ``RepublicationIntrouvable`` si la Republication n'existe pas.
    """
    republication = db.get(Republication, republication_id)
    if republication is None:
        raise RepublicationIntrouvable(republication_id)

    republication.statut = "published"
    avancer_statut(republication.article.source, "published")

    db.commit()
    db.refresh(republication)
    return republication
