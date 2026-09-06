"""Service de l'étape « Qualifier ».

Crée ou met à jour la Qualification d'une Source existante. Relation 1-1
(voir ``app.models.qualification``) : une Source déjà qualifiée voit sa
Qualification mise à jour, jamais dupliquée (violerait l'unicité de
``source_id``).
"""

from sqlalchemy.orm import Session

from app.models import Qualification, Source
from app.models.source import STATUTS
from app.services.ranger import SourceIntrouvable


def qualifier_source(
    db: Session,
    source_id: int,
    categorie: str,
    legitimite: int,
    interet: int,
    qualified_by: str,
) -> Qualification:
    """Crée ou met à jour la Qualification liée à ``source_id``.

    ``Source.statut`` avance vers ``"qualified"`` seulement si l'étape
    actuelle est *avant* dans ``STATUTS`` (même règle que ``ranger_source``) :
    une Source déjà rangée, digérée ou republiée garde son statut, seule sa
    Qualification change.

    Lève ``SourceIntrouvable`` si la Source n'existe pas.
    """
    source = db.get(Source, source_id)
    if source is None:
        raise SourceIntrouvable(source_id)

    # ``source.qualification`` : relation 1-1 déjà définie sur Source. None si
    # aucune Qualification n'existe encore -> on la crée ; sinon on met à jour
    # celle qui existe (upsert, pas de doublon).
    qualification = source.qualification
    if qualification is None:
        qualification = Qualification(source_id=source_id)
        db.add(qualification)

    qualification.categorie = categorie
    qualification.legitimite = legitimite
    qualification.interet = interet
    qualification.qualified_by = qualified_by

    # ``STATUTS.index(x)`` = position de x dans l'ordre du workflow : plus
    # petit = plus tôt. On n'avance le statut que si on n'a pas déjà dépassé
    # l'étape "qualified" (ex. une Source "digested" reste "digested").
    if STATUTS.index(source.statut) < STATUTS.index("qualified"):
        source.statut = "qualified"

    db.commit()
    db.refresh(qualification)
    return qualification
