"""Service de listing des Sources."""

from sqlalchemy.orm import Session

from app.models import Source


def lister_sources(
    db: Session, statut: str | None = None, folder_id: int | None = None
) -> list[Source]:
    """Renvoie les Sources correspondant aux filtres fournis, plus récentes d'abord.

    ``statut`` et ``folder_id`` sont optionnels : un filtre n'est ajouté à la
    requête que s'il est fourni (différent de None) ; sans aucun filtre,
    toutes les Sources sont renvoyées.
    """
    query = db.query(Source)

    if statut is not None:
        query = query.filter(Source.statut == statut)

    if folder_id is not None:
        query = query.filter(Source.folder_id == folder_id)

    # ``.desc()`` : tri décroissant -> les Sources les plus récentes en premier.
    return query.order_by(Source.created_at.desc()).all()
