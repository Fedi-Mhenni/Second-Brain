"""Endpoints « sources » regroupés sous ``prefix="/sources"`` :

- ``GET  /sources``                  — listing, filtres ``?statut=`` / ``?folder_id=``
- ``PATCH /sources/{id}/folder``     — Ranger : rattache la Source à un Folder
- ``POST  /sources/{id}/digest``     — Digérer (manuel) : crée/met à jour l'Article lié
- ``POST  /sources/{id}/digest/auto`` — Digérer (auto) : résumé généré par LLMProvider
- ``POST  /sources/{id}/qualification`` — Qualifier : crée/met à jour la Qualification

``SourceIntrouvable`` existe dans deux services (``ranger`` et ``digerer``) et
n'a pas été fusionné (hors périmètre) : on importe les deux, avec alias, et
chaque route attrape celle de son propre service. ``qualifier`` réutilise
celle de ``ranger`` plutôt que d'en redéfinir une 3e (voir ce module).
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.digerer import (
    AucunContenuFourni,
    SourceIntrouvable as SourceIntrouvableDigest,
    digerer_source,
    digerer_source_auto,
)
from app.services.qualifier import qualifier_source
from app.services.ranger import (
    FolderIntrouvable,
    SourceIntrouvable as SourceIntrouvableRanger,
    ranger_source,
)
from app.services.sources import lister_sources

router = APIRouter(prefix="/sources", tags=["sources"])


class RangerSourceIn(BaseModel):
    """Corps de la requête de rangement : le Folder auquel rattacher la Source."""

    folder_id: int


class DigestSourceIn(BaseModel):
    """Corps de la requête de digestion : les champs de l'Article à écrire.

    Les trois sont optionnels ; un champ absent (ou vide) ne modifie pas la
    valeur déjà enregistrée. Au moins un des trois doit porter du contenu réel.
    """

    titre: str | None = None
    contenu: str | None = None
    resume: str | None = None


class SourceOut(BaseModel):
    """Une Source telle que renvoyée par l'API (sans son contenu, potentiellement volumineux)."""

    id: int
    url: str | None
    titre: str | None
    statut: str
    folder_id: int | None


class ArticleOut(BaseModel):
    """Réponse de la digestion : l'Article tel qu'il vient d'être créé/mis à jour."""

    id: int
    source_id: int
    titre: str | None
    contenu: str | None
    resume: str | None


class ArticleAutoOut(ArticleOut):
    """Comme ``ArticleOut``, plus le nom du provider LLM ayant produit le résumé.

    ``provider`` est transitoire (pas une colonne) : "GeminiProvider" si le vrai
    appel Gemini a réussi, "MockProvider" en repli (ou si aucune clé n'est configurée).
    """

    provider: str


class QualifierSourceIn(BaseModel):
    """Corps de la requête de qualification.

    ``Literal`` sur ``categorie``/``qualified_by`` : FastAPI renvoie 422 tout
    seul pour une valeur hors liste, pas de validation manuelle à écrire.
    ``Field(ge=1, le=5)`` sur ``legitimite``/``interet`` : mêmes bornes que le
    ``CheckConstraint`` du modèle ``Qualification`` (app/models/qualification.py)
    — une valeur hors échelle est rejetée par le schéma avant même d'atteindre
    la base, qui la refuserait de toute façon.
    """

    categorie: Literal["metier", "pro", "perso", "culture"]
    legitimite: int = Field(ge=1, le=5)
    interet: int = Field(ge=1, le=5)
    qualified_by: Literal["ai", "manual"] = "manual"


class QualificationOut(BaseModel):
    """Une Qualification telle que renvoyée par l'API."""

    id: int
    source_id: int
    categorie: str
    legitimite: int
    interet: int
    qualified_by: str


@router.get("", response_model=list[SourceOut])
def lister_sources_route(
    # ``Query(default=None, ...)`` : ce sont des paramètres d'URL optionnels
    # (``?statut=...`` et ``?folder_id=...``), pas des paramètres de chemin ni
    # de corps de requête. FastAPI les détecterait comme tels même sans
    # ``Query(...)`` explicite ; on l'utilise ici pour leur ajouter une
    # description visible dans Swagger.
    statut: str | None = Query(
        default=None, description="Filtre par statut (ex. 'captured', 'ranged')"
    ),
    folder_id: int | None = Query(
        default=None, description="Filtre par identifiant de dossier"
    ),
    db: Session = Depends(get_db),
):
    """Liste les Sources, filtrées par statut et/ou dossier si précisé."""
    sources = lister_sources(db, statut=statut, folder_id=folder_id)
    # Construction explicite de chaque SourceOut depuis l'objet ORM, comme
    # pour Folder dans app/routes/folders.py (même convention dans le projet).
    return [
        SourceOut(
            id=s.id, url=s.url, titre=s.titre, statut=s.statut, folder_id=s.folder_id
        )
        for s in sources
    ]


@router.patch(
    "/{source_id}/folder",
    response_model=SourceOut,
    status_code=status.HTTP_200_OK,
)
def ranger_source_route(
    source_id: int, payload: RangerSourceIn, db: Session = Depends(get_db)
):
    """Range une Source existante dans un Folder existant.

    Le statut passe à ``"ranged"`` seulement si la Source n'a pas déjà
    dépassé cette étape du workflow (voir ``app.services.ranger``).
    """
    try:
        source = ranger_source(db, source_id, payload.folder_id)
    except SourceIntrouvableRanger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable"
        )
    except FolderIntrouvable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder introuvable"
        )

    return SourceOut(
        id=source.id,
        url=source.url,
        titre=source.titre,
        statut=source.statut,
        folder_id=source.folder_id,
    )


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
    except SourceIntrouvableDigest:
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


@router.post(
    "/{source_id}/digest/auto",
    response_model=ArticleAutoOut,
    status_code=status.HTTP_200_OK,
)
def digerer_source_auto_route(source_id: int, db: Session = Depends(get_db)):
    """Digère la Source automatiquement : résumé généré par le ``LLMProvider`` courant.

    Aucun body. 404 si la Source n'existe pas, 400 si son ``contenu_brut`` est
    vide (voir ``app.services.digerer``). Réutilise l'upsert et l'avancement de
    statut de la digestion manuelle.
    """
    try:
        article, provider = digerer_source_auto(db, source_id)
    except SourceIntrouvableDigest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable"
        )
    except AucunContenuFourni:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun contenu à digérer"
        )

    return ArticleAutoOut(
        id=article.id,
        source_id=article.source_id,
        titre=article.titre,
        contenu=article.contenu,
        resume=article.resume,
        provider=provider,
    )


@router.post(
    "/{source_id}/qualification",
    response_model=QualificationOut,
    status_code=status.HTTP_200_OK,
)
def qualifier_source_route(
    source_id: int, payload: QualifierSourceIn, db: Session = Depends(get_db)
):
    """Crée ou met à jour la Qualification d'une Source existante.

    404 si la Source n'existe pas (voir ``app.services.qualifier``).
    """
    try:
        qualification = qualifier_source(
            db,
            source_id,
            categorie=payload.categorie,
            legitimite=payload.legitimite,
            interet=payload.interet,
            qualified_by=payload.qualified_by,
        )
    except SourceIntrouvableRanger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable"
        )

    return QualificationOut(
        id=qualification.id,
        source_id=qualification.source_id,
        categorie=qualification.categorie,
        legitimite=qualification.legitimite,
        interet=qualification.interet,
        qualified_by=qualification.qualified_by,
    )
