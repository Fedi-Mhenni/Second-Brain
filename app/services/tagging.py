"""Service de l'étape « Ranger » (tags) : associe des Tags à un Article.

``ArticleIntrouvable`` est réutilisée depuis ``app.services.republier`` (pas
redéfinie ici) : les deux services agissent sur le même Article, une seule
définition de cette exception suffit — inutile de reproduire la duplication
``SourceIntrouvable`` (Qualifier/Ranger/Digérer), déjà connue comme dette
technique sur ce projet.
"""

from sqlalchemy.orm import Session, joinedload

from app.models import Article, ArticleTag, Tag
from app.services.republier import ArticleIntrouvable


def _recuperer_ou_creer_tag(db: Session, nom: str) -> Tag:
    """Renvoie le Tag existant portant ``nom``, ou le crée s'il n'existe pas encore.

    ``Tag.nom`` est unique (voir app/models/tag.py) : deux Articles tagués
    du même mot partagent la même ligne Tag, jamais de doublon.
    """
    tag = db.query(Tag).filter_by(nom=nom).one_or_none()
    if tag is None:
        tag = Tag(nom=nom)
        db.add(tag)
        # flush (pas commit) : récupère tag.id tout de suite pour construire
        # l'ArticleTag ci-dessous, sans clore la transaction en cours.
        db.flush()
    return tag


def taguer_article(
    db: Session, article_id: int, nom: str, added_by: str
) -> ArticleTag:
    """Associe le Tag ``nom`` à l'Article ``article_id``.

    Si le lien (article_id, tag_id) existe déjà, il n'est PAS modifié : son
    ``added_by`` d'origine est conservé même si l'appel courant en apporte un
    différent (ex. une suggestion IA qui reproduit un tag déjà confirmé à la
    main ne doit pas effacer cette confirmation ; à l'inverse, un ajout
    manuel qui recoupe une suggestion IA n'apporte rien de plus à enregistrer).
    Le lien existant est renvoyé tel quel.

    Lève ``ArticleIntrouvable`` si l'Article n'existe pas.
    """
    article = db.get(Article, article_id)
    if article is None:
        raise ArticleIntrouvable(article_id)

    tag = _recuperer_ou_creer_tag(db, nom)

    lien = (
        db.query(ArticleTag)
        .filter_by(article_id=article_id, tag_id=tag.id)
        .one_or_none()
    )
    if lien is not None:
        return lien

    lien = ArticleTag(article_id=article_id, tag_id=tag.id, added_by=added_by)
    db.add(lien)
    db.commit()
    db.refresh(lien)
    return lien


def lister_tags_article(db: Session, article_id: int) -> list[ArticleTag]:
    """Renvoie les ArticleTag de l'Article, triés par date d'ajout.

    ``joinedload(ArticleTag.tag)`` : la route accède à ``article_tag.tag.nom``
    pour chaque lien -> sans eager-loading, chaque accès déclencherait sa
    propre requête (N+1), même raisonnement que ``joinedload(Source.folder)``
    dans app/routes/web.py.

    Lève ``ArticleIntrouvable`` si l'Article n'existe pas.
    """
    article = db.get(Article, article_id)
    if article is None:
        raise ArticleIntrouvable(article_id)

    return (
        db.query(ArticleTag)
        .options(joinedload(ArticleTag.tag))
        .filter_by(article_id=article_id)
        .order_by(ArticleTag.created_at)
        .all()
    )
