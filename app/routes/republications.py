"""Endpoints « republications » regroupés sous ``prefix="/republications"`` :

- ``PATCH /republications/{id}/publier`` — marque une Republication comme
  publiée (publication manuelle, voir app/services/republier.py) et fait
  avancer la Source associée.

Fichier séparé de ``app/routes/articles.py`` : cette route ne crée pas de
Republication (donc n'est pas rattachée à un Article dans son chemin), elle
agit sur une Republication existante identifiée par son propre id — un
routeur dédié à ce préfixe évite d'alourdir articles.py avec un chemin qui
ne lui appartient pas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.articles import RepublicationOut
from app.services.republier import RepublicationIntrouvable, publier_republication

router = APIRouter(prefix="/republications", tags=["republications"])


@router.patch("/{republication_id}/publier", response_model=RepublicationOut)
def publier_republication_route(
    republication_id: int, db: Session = Depends(get_db)
):
    """Marque la Republication comme publiée.

    Pas d'appel LinkedIn/X (décision actée au cadrage) : ce endpoint ne fait
    qu'exposer en JSON ce que la page HTML (``POST /republications/{id}/publier``,
    app/routes/web.py) fait déjà pour un navigateur — même service, même
    règle d'avancement de la Source (``avancer_statut``, appliquée dans
    ``publier_republication``).

    404 si la Republication n'existe pas.
    """
    try:
        republication = publier_republication(db, republication_id)
    except RepublicationIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Republication introuvable"
        )

    return RepublicationOut(
        id=republication.id,
        article_id=republication.article_id,
        canal=republication.canal,
        brouillon=republication.brouillon,
        statut=republication.statut,
        posture=republication.posture,
    )
