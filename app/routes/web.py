"""Routes HTML server-rendered : dashboard, formulaire de capture, liste des sources.

Pourquoi un fichier séparé de ``app/routes/capture.py`` plutôt que d'ajouter
ces routes au même router : les deux fichiers servent deux contrats et deux
publics différents qui ne doivent pas se contraindre l'un l'autre.
``capture.py`` est une API JSON (corps et réponses typés par des modèles
Pydantic, codes 201/409, pensée pour un client programmatique) ; ce fichier
sert des pages HTML à un navigateur (formulaires ``multipart/form-data``,
réponses de redirection 303). Les mélanger dans un même router obligerait
soit à dupliquer chaque route en deux versions, soit à faire porter à une
seule route la négociation de contenu (JSON vs HTML) — plus complexe pour un
gain nul ici. Les deux fichiers restent alignés parce qu'ils appellent les
mêmes fonctions de service (``app.services.capture``) : la logique de
capture n'existe qu'à un seul endroit, seule la façon de la présenter change.

Ces routes elles-mêmes ne portent aucune logique métier (règle de
CLAUDE.md) : chaque route appelle le service puis rend un template ou
redirige, rien de plus. ``POST /capture`` (ici) et ``POST /capture/url`` /
``POST /capture/note`` (API JSON) sont des chemins distincts par
construction : aucun risque de collision de route entre les deux fichiers.
Idem pour ``GET /liste`` (ici, page HTML de listing) face à ``GET /sources``
(API JSON, ``app/routes/sources.py``) : le coéquipier a tranché que le
contrat JSON garde le chemin d'origine (déjà utilisé par Ranger et Digérer),
c'est donc la page HTML qui porte un nom distinct.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Republication, Source
from app.services.capture import (
    SchemaUrlNonAutorise,
    UrlDejaCaptee,
    capture_note,
    capture_url,
)
from app.services.digerer import (
    AucunContenuFourni,
    SourceIntrouvable as SourceIntrouvableDigest,
    digerer_source,
    digerer_source_auto,
)
from app.services.folders import lister_folders
from app.services.qualifier import qualifier_source, qualifier_source_auto
from app.services.ranger import (
    FolderIntrouvable,
    SourceIntrouvable as SourceIntrouvableRanger,
    ranger_source,
)
from app.services.republier import (
    ArticleIntrouvable,
    RepublicationIntrouvable,
    publier_republication,
    republier_article,
)
from app.services.tagging import taguer_article

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    """Récupère l'instance Jinja2Templates configurée dans ``app/main.py``.

    Passe par ``request.app.state`` plutôt que d'instancier Jinja2Templates
    ici : une seule instance pour toute l'application (voir le commentaire
    dans main.py), et ça évite d'avoir à importer main.py depuis ce module
    alors que main.py importe déjà ce module pour brancher son router.
    """
    return request.app.state.templates


@router.get("/")
def dashboard_route(request: Request, db: Session = Depends(get_db)):
    # Lecture directe sans passer par un service : un comptage brut pour
    # affichage n'est pas une décision métier, juste une projection.
    total = db.query(Source).count()
    return _templates(request).TemplateResponse(
        request, "dashboard.html", {"total": total}
    )


@router.get("/liste")
def liste_sources_route(request: Request, db: Session = Depends(get_db)):
    # Idem : lister/trier pour affichage n'est pas de la logique métier.
    # ``joinedload(Source.folder)`` : sources.html accède à source.folder.nom
    # pour chaque source dans sa boucle. Sans eager-loading, chaque accès à
    # ``source.folder`` déclencherait sa propre requête (lazy loading) ->
    # une requête en plus par source rangée en base (N+1). Le joinedload
    # récupère tout en une seule requête (LEFT JOIN sources/folders).
    sources = (
        db.query(Source)
        .options(joinedload(Source.folder))
        .order_by(Source.created_at.desc())
        .all()
    )
    return _templates(request).TemplateResponse(
        request, "sources.html", {"sources": sources}
    )


@router.get("/liste/{source_id}")
def fiche_source_route(
    source_id: int,
    request: Request,
    db: Session = Depends(get_db),
    erreur: str | None = None,
):
    """Vue détail d'une Source : tout ce que le workflow sait d'elle, et les
    actions pour la faire avancer (Qualifier, Ranger, Digérer).

    Lecture directe (pas de service) : un ``db.get`` par identifiant n'est
    pas une décision métier, même raisonnement que ``dashboard_route`` et
    ``liste_sources_route`` ci-dessus.
    """
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source introuvable")

    return _templates(request).TemplateResponse(
        request,
        "fiche_source.html",
        {"source": source, "folders": lister_folders(db), "erreur": erreur},
    )


@router.post("/liste/{source_id}/qualifier")
def fiche_qualifier_manuel_route(
    source_id: int,
    db: Session = Depends(get_db),
    categorie: Literal["metier", "pro", "perso", "culture"] = Form(...),
    legitimite: int = Form(..., ge=1, le=5),
    interet: int = Form(..., ge=1, le=5),
):
    """Qualifie manuellement la Source, puis revient sur sa fiche.

    Mêmes contraintes que ``QualifierSourceIn`` (API JSON) : validation
    d'entrée par FastAPI/Pydantic, pas une règle métier écrite ici.
    """
    try:
        qualifier_source(
            db,
            source_id,
            categorie=categorie,
            legitimite=legitimite,
            interet=interet,
            qualified_by="manual",
        )
    except SourceIntrouvableRanger:
        raise HTTPException(status_code=404, detail="Source introuvable")

    return RedirectResponse(f"/liste/{source_id}", status_code=303)


@router.post("/liste/{source_id}/qualifier/auto")
def fiche_qualifier_auto_route(source_id: int, db: Session = Depends(get_db)):
    """Déclenche la qualification automatique (LLMProvider), revient sur la fiche."""
    try:
        qualifier_source_auto(db, source_id)
    except SourceIntrouvableRanger:
        raise HTTPException(status_code=404, detail="Source introuvable")

    return RedirectResponse(f"/liste/{source_id}", status_code=303)


@router.post("/liste/{source_id}/ranger")
def fiche_ranger_route(
    source_id: int, db: Session = Depends(get_db), folder_id: int = Form(...)
):
    """Range la Source dans le Folder choisi, revient sur sa fiche."""
    try:
        ranger_source(db, source_id, folder_id)
    except SourceIntrouvableRanger:
        raise HTTPException(status_code=404, detail="Source introuvable")
    except FolderIntrouvable:
        raise HTTPException(status_code=404, detail="Folder introuvable")

    return RedirectResponse(f"/liste/{source_id}", status_code=303)


@router.post("/liste/{source_id}/digerer/auto")
def fiche_digerer_auto_route(source_id: int, db: Session = Depends(get_db)):
    """Déclenche la digestion automatique (LLMProvider), revient sur la fiche."""
    try:
        digerer_source_auto(db, source_id)
    except SourceIntrouvableDigest:
        raise HTTPException(status_code=404, detail="Source introuvable")
    except AucunContenuFourni:
        # La Source n'a pas de contenu_brut exploitable : on revient sur la
        # fiche avec un indicateur d'erreur plutôt que de laisser planter.
        return RedirectResponse(
            f"/liste/{source_id}?erreur=aucun_contenu", status_code=303
        )

    return RedirectResponse(f"/liste/{source_id}", status_code=303)


@router.post("/liste/{source_id}/digerer")
def fiche_digerer_manuel_route(
    source_id: int,
    db: Session = Depends(get_db),
    resume: str = Form(default=""),
    contenu: str = Form(default=""),
):
    """Digestion manuelle depuis la fiche : résumé et/ou contenu collé à la main.

    ``contenu`` n'est proposé par le template que lorsque l'extraction
    automatique a échoué (``source.contenu_brut`` vide) : on le remonte alors
    sur la Source pour que « Digérer avec l'IA » redevienne possible ensuite,
    en plus de le passer à ``digerer_source``.
    """
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source introuvable")

    if contenu.strip() and not (source.contenu_brut or "").strip():
        source.contenu_brut = contenu.strip()

    try:
        digerer_source(db, source_id, contenu=contenu or None, resume=resume or None)
    except SourceIntrouvableDigest:
        raise HTTPException(status_code=404, detail="Source introuvable")
    except AucunContenuFourni:
        return RedirectResponse(
            f"/liste/{source_id}?erreur=digestion_vide", status_code=303
        )

    return RedirectResponse(f"/liste/{source_id}", status_code=303)


@router.post("/liste/{source_id}/republier")
def fiche_republier_route(
    source_id: int,
    db: Session = Depends(get_db),
    canal: Literal["linkedin", "x"] = Form(...),
    posture: Literal["personal_branding", "entreprise"] = Form(...),
    brouillon: str = Form(...),
):
    """Crée un brouillon de Republication pour l'Article de cette Source.

    N'existe que si la Source a un Article (le formulaire n'est rendu que
    dans ce cas, voir fiche_source.html) : 404 direct sinon, pas besoin de
    passer par ``republier_article``/``ArticleIntrouvable`` pour un cas que
    l'UI n'expose jamais. Redirige vers la page de la republication créée,
    pas vers la fiche, pour enchaîner directement sur copier/publier.
    """
    source = db.get(Source, source_id)
    if source is None or source.article is None:
        raise HTTPException(status_code=404, detail="Source introuvable")

    republication = republier_article(
        db, source.article.id, canal=canal, brouillon=brouillon, posture=posture
    )
    return RedirectResponse(f"/republications/{republication.id}", status_code=303)


@router.post("/liste/{source_id}/tags")
def fiche_tag_route(
    source_id: int,
    db: Session = Depends(get_db),
    nom: str = Form(...),
    added_by: Literal["ai", "manual"] = Form(default="manual"),
):
    """Associe un Tag à l'Article de cette Source, revient sur sa fiche.

    Même garde que fiche_republier_route : le formulaire n'est rendu que si
    source.article existe (voir fiche_source.html). ``ArticleIntrouvable``
    reste catchée malgré tout, même pattern que les autres actions de ce
    fichier (Qualifier/Ranger/Digérer) : chaque service traduit sa propre
    exception, indépendamment de la garde déjà posée ici.
    """
    source = db.get(Source, source_id)
    if source is None or source.article is None:
        raise HTTPException(status_code=404, detail="Source introuvable")

    try:
        taguer_article(db, source.article.id, nom=nom, added_by=added_by)
    except ArticleIntrouvable:
        raise HTTPException(status_code=404, detail="Article introuvable")

    return RedirectResponse(f"/liste/{source_id}", status_code=303)


@router.get("/republications")
def liste_republications_route(request: Request, db: Session = Depends(get_db)):
    # Lecture directe (pas de service) : lister/trier pour affichage n'est
    # pas de la logique métier, même raisonnement que liste_sources_route.
    republications = (
        db.query(Republication).order_by(Republication.created_at.desc()).all()
    )
    return _templates(request).TemplateResponse(
        request, "republications.html", {"republications": republications}
    )


@router.get("/republications/{republication_id}")
def republication_route(
    republication_id: int, request: Request, db: Session = Depends(get_db)
):
    republication = db.get(Republication, republication_id)
    if republication is None:
        raise HTTPException(status_code=404, detail="Republication introuvable")

    return _templates(request).TemplateResponse(
        request, "republication.html", {"republication": republication}
    )


@router.post("/republications/{republication_id}/publier")
def republication_publier_route(
    republication_id: int, db: Session = Depends(get_db)
):
    """Marque la Republication comme publiée (publication manuelle, pas d'API)."""
    try:
        publier_republication(db, republication_id)
    except RepublicationIntrouvable:
        raise HTTPException(status_code=404, detail="Republication introuvable")

    return RedirectResponse(f"/republications/{republication_id}", status_code=303)


@router.get("/capture")
def formulaire_capture_route(request: Request, erreur: str | None = None):
    return _templates(request).TemplateResponse(
        request, "capture.html", {"erreur": erreur}
    )


@router.post("/capture")
def soumettre_capture_route(
    db: Session = Depends(get_db),
    url: str = Form(default=""),
    texte: str = Form(default=""),
):
    """Traite le formulaire de capture (URL ou note) puis redirige.

    Le formulaire n'envoie qu'un seul des deux champs à la fois (deux
    ``<form>`` distincts dans ``capture.html``) : on regarde lequel est
    renseigné pour choisir le service à appeler.
    """
    if url.strip():
        try:
            capture_url(db, url.strip())
        except UrlDejaCaptee:
            # Cas d'échec géré explicitement : on repasse par le formulaire
            # avec un indicateur d'erreur plutôt que de laisser planter.
            return RedirectResponse("/capture?erreur=deja_captee", status_code=303)
        except SchemaUrlNonAutorise:
            # Le formulaire envoie une chaîne brute, sans la validation
            # Pydantic ``HttpUrl`` de l'API JSON : c'est le service qui
            # protège ce chemin (voir app/services/capture.py).
            return RedirectResponse("/capture?erreur=schema_invalide", status_code=303)
    elif texte.strip():
        capture_note(db, texte.strip())

    return RedirectResponse("/liste", status_code=303)
