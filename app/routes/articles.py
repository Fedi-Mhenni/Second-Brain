"""Endpoints « articles » regroupés sous ``prefix="/articles"`` :

- ``POST /articles/{id}/republications`` — Republier : crée un brouillon de Republication
- ``POST /articles/{id}/tags`` — Ranger (tags) : associe un Tag à l'Article
- ``GET /articles/{id}/tags`` — liste les tags de l'Article
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.republier import ArticleIntrouvable, republier_article
from app.services.tagging import lister_tags_article, taguer_article

router = APIRouter(prefix="/articles", tags=["articles"])


class RepublicationIn(BaseModel):
    """Corps de la requête de republication.

    ``Literal`` sur ``canal``/``posture`` : FastAPI renvoie 422 tout seul
    pour une valeur hors liste, cohérent avec ``CANAUX``/``POSTURES`` dans
    ``app/models/republication.py``.
    """

    canal: Literal["linkedin", "x"]
    brouillon: str
    posture: Literal["personal_branding", "entreprise"]


class RepublicationOut(BaseModel):
    """Une Republication telle que renvoyée par l'API."""

    id: int
    article_id: int
    canal: str
    brouillon: str
    statut: str
    posture: str


@router.post(
    "/{article_id}/republications",
    response_model=RepublicationOut,
    status_code=status.HTTP_201_CREATED,
)
def republier_article_route(
    article_id: int, payload: RepublicationIn, db: Session = Depends(get_db)
):
    """Crée une nouvelle Republication pour l'Article existant.

    404 si l'Article n'existe pas (voir ``app.services.republier``).
    Toujours une création : pas de contrainte d'unicité, un Article peut
    être republié plusieurs fois (canaux/postures différents).
    """
    try:
        republication = republier_article(
            db,
            article_id,
            canal=payload.canal,
            brouillon=payload.brouillon,
            posture=payload.posture,
        )
    except ArticleIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable"
        )

    return RepublicationOut(
        id=republication.id,
        article_id=republication.article_id,
        canal=republication.canal,
        brouillon=republication.brouillon,
        statut=republication.statut,
        posture=republication.posture,
    )


class TagIn(BaseModel):
    """Corps de la requête de tagging.

    ``added_by`` par défaut à ``"manual"`` : un tag posé sans précision vient
    d'un ajout humain, pas d'une suggestion IA (celle-ci passe explicitement
    ``"ai"``, voir l'étape Digérer/Qualifier).
    """

    nom: str
    added_by: Literal["ai", "manual"] = "manual"


class TagOut(BaseModel):
    """Un Tag associé à un Article, tel que renvoyé par l'API.

    ``id``/``nom`` viennent du Tag ; ``added_by`` vient du lien ArticleTag
    (propriété de l'association, pas du Tag lui-même — voir son docstring).
    """

    id: int
    nom: str
    added_by: str


@router.post(
    "/{article_id}/tags",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
)
def taguer_article_route(
    article_id: int, payload: TagIn, db: Session = Depends(get_db)
):
    """Associe un Tag à l'Article existant.

    404 si l'Article n'existe pas. Un lien déjà existant pour ce couple
    (Article, Tag) est renvoyé tel quel, sans écraser son ``added_by``
    d'origine (voir app/services/tagging.py).
    """
    try:
        lien = taguer_article(
            db, article_id, nom=payload.nom, added_by=payload.added_by
        )
    except ArticleIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable"
        )

    return TagOut(id=lien.tag_id, nom=lien.tag.nom, added_by=lien.added_by)


@router.get("/{article_id}/tags", response_model=list[TagOut])
def lister_tags_article_route(article_id: int, db: Session = Depends(get_db)):
    """Liste les tags de l'Article, triés par date d'ajout.

    404 si l'Article n'existe pas (distingue explicitement ce cas d'un
    Article existant sans aucun tag, qui renvoie une liste vide).
    """
    try:
        liens = lister_tags_article(db, article_id)
    except ArticleIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable"
        )

    return [TagOut(id=lien.tag_id, nom=lien.tag.nom, added_by=lien.added_by) for lien in liens]
