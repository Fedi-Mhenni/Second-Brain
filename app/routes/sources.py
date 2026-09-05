"""Endpoint de l'étape « Digérer » : ``POST /sources/{source_id}/digest``.

Cette branche part de ``main`` : ni ``feat/ranger-source`` (PATCH .../folder)
ni ``feat/list-sources`` (GET /sources) ne sont mergées ici. Les trois routes
« /sources/... » finiront dans ce même fichier au moment de merger les
branches — un conflit simple à réconcilier, pas un problème de logique.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.digerer import AucunContenuFourni, SourceIntrouvable, digerer_source

router = APIRouter(prefix="/sources", tags=["sources"])


class DigestSourceIn(BaseModel):
    """Corps de la requête : les champs de l'Article à écrire.

    Les trois sont optionnels ; un champ absent (ou vide) ne modifie pas la
    valeur déjà enregistrée. Au moins un des trois doit porter du contenu réel.
    """

    titre: str | None = None
    contenu: str | None = None
    resume: str | None = None


class ArticleOut(BaseModel):
    """Réponse : l'Article tel qu'il vient d'être créé/mis à jour."""

    id: int
    source_id: int
    titre: str | None
    contenu: str | None
    resume: str | None


@router.post(
    "/{source_id}/digest",
    response_model=ArticleOut,
    status_code=status.HTTP_200_OK,
)
def digerer_source_route(
    source_id: int, payload: DigestSourceIn, db: Session = Depends(get_db)
):
    """Crée ou met à jour l'Article lié à la Source, avance son statut si besoin.

    404 si la Source n'existe pas, 400 si les trois champs sont vides
    (voir ``app.services.digerer``).
    """
    try:
        article = digerer_source(
            db,
            source_id,
            titre=payload.titre,
            contenu=payload.contenu,
            resume=payload.resume,
        )
    except SourceIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable"
        )
    except AucunContenuFourni:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun contenu fourni pour la digestion",
        )

    return ArticleOut(
        id=article.id,
        source_id=article.source_id,
        titre=article.titre,
        contenu=article.contenu,
        resume=article.resume,
    )
