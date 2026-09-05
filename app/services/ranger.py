"""Service de l'étape « Ranger ».

Assigne une Source existante à un Folder existant. Le statut de la Source
n'avance vers ``"ranged"`` que s'il n'a pas déjà dépassé cette étape (voir
``ranger_source``) : rattacher à un autre dossier une Source déjà qualifiée,
digérée ou republiée ne doit pas la faire reculer dans le workflow.
"""

from sqlalchemy.orm import Session

from app.models import Folder, Source
from app.models.source import STATUTS


class SourceIntrouvable(Exception):
    """Levée quand la Source demandée n'existe pas."""

    def __init__(self, source_id: int):
        self.source_id = source_id
        super().__init__(f"Source introuvable (id={source_id})")


class FolderIntrouvable(Exception):
    """Levée quand le Folder demandé n'existe pas."""

    def __init__(self, folder_id: int):
        self.folder_id = folder_id
        super().__init__(f"Folder introuvable (id={folder_id})")


def ranger_source(db: Session, source_id: int, folder_id: int) -> Source:
    """Range une Source dans un Folder.

    ``folder_id`` est toujours affecté. ``statut`` ne passe à ``"ranged"`` que
    si l'étape actuelle est *avant* "ranged" dans ``STATUTS`` (donc
    "captured" ou "qualified") : une Source déjà rangée, digérée ou
    republiée garde son statut, seul son dossier change.

    Lève ``SourceIntrouvable`` / ``FolderIntrouvable`` si l'un des deux n'existe pas.
    """
    # ``Session.get(Modele, cle_primaire)`` : recherche directe par clé
    # primaire, renvoie None si absent (contrairement à ``.one()``, qui lève
    # une exception) — pratique ici puisqu'on veut détecter l'absence nous-mêmes.
    source = db.get(Source, source_id)
    if source is None:
        raise SourceIntrouvable(source_id)

    folder = db.get(Folder, folder_id)
    if folder is None:
        raise FolderIntrouvable(folder_id)

    source.folder_id = folder_id

    # ``STATUTS.index(x)`` = position de x dans l'ordre du workflow : plus
    # petit = plus tôt. On n'avance le statut que si on n'a pas déjà dépassé
    # l'étape "ranged" (ex. une Source "digested" reste "digested").
    if STATUTS.index(source.statut) < STATUTS.index("ranged"):
        source.statut = "ranged"

    # Pas besoin de toucher updated_at à la main : ``onupdate=utcnow`` (sur
    # le modèle Source) le fait tout seul dès que la ligne modifiée est commitée.
    db.commit()
    db.refresh(source)
    return source
