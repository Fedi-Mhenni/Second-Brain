"""Endpoints « articles » regroupés sous ``prefix="/articles"`` :

- ``POST /articles/{id}/republications`` — Republier : crée un brouillon de Republication
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.republier import ArticleIntrouvable, republier_article

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
