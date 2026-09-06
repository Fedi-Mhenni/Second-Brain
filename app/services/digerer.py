"""Service de l'étape « Digérer ».

Crée ou met à jour l'Article lié à une Source (relation un-à-un). Le résumé
et le contenu sont écrits à la main pour l'instant (pas d'IA : LLMProvider
n'existe pas encore) ; seuls les champs fournis sont modifiés, les autres
gardent leur valeur existante (utile pour compléter un Article en plusieurs
appels).
"""

from sqlalchemy.orm import Session

from app.models import Article, Source
from app.models.source import STATUTS


class SourceIntrouvable(Exception):
    """Levée quand la Source demandée n'existe pas.

    Redéfinie ici (comme dans ``app.services.ranger``, qui n'existe pas
    encore sur cette branche) : les deux versions seront à réconcilier au
    moment de merger les branches Ranger / Digérer.
    """

    def __init__(self, source_id: int):
        self.source_id = source_id
        super().__init__(f"Source introuvable (id={source_id})")


class AucunContenuFourni(Exception):
    """Levée quand titre, contenu et resume sont tous vides : rien à digérer."""


def _nettoie(valeur: str | None) -> str | None:
    """Normalise une chaîne reçue du client.

    Renvoie None si ``valeur`` est absente, vide, ou ne contient que des
    espaces ; sinon la valeur débarrassée de ses espaces de début/fin.
    """
    if valeur is None:
        return None
    valeur = valeur.strip()
    return valeur or None


def digerer_source(
    db: Session,
    source_id: int,
    titre: str | None = None,
    contenu: str | None = None,
    resume: str | None = None,
) -> Article:
    """Crée ou met à jour l'Article lié à ``source_id``.

    Seuls les champs fournis (non vides après nettoyage) sont écrits.
    ``Source.statut`` avance vers ``"digested"`` seulement si l'étape
    actuelle est *avant* dans ``STATUTS`` (même règle que Ranger) — jamais si
    aucun contenu réel n'est fourni, puisque la fonction refuse ce cas avant
    d'aller plus loin.

    Lève ``SourceIntrouvable`` si la Source n'existe pas, ``AucunContenuFourni``
    si les trois champs sont vides.
    """
    source = db.get(Source, source_id)
    if source is None:
        raise SourceIntrouvable(source_id)

    titre = _nettoie(titre)
    contenu = _nettoie(contenu)
    resume = _nettoie(resume)

    # Refuse de créer un Article vide ou de faire avancer le statut pour rien :
    # au moins un des trois champs doit porter du contenu réel.
    if titre is None and contenu is None and resume is None:
        raise AucunContenuFourni()

    # ``source.article`` : la relation un-à-un déjà définie sur Source. None
    # si aucun Article n'existe encore pour cette Source -> on le crée ; sinon
    # on met à jour l'Article existant (upsert, pas de doublon).
    article = source.article
    if article is None:
        article = Article(source_id=source_id)
        db.add(article)

    if titre is not None:
        article.titre = titre
    if contenu is not None:
        article.contenu = contenu
    if resume is not None:
        article.resume = resume

    if STATUTS.index(source.statut) < STATUTS.index("digested"):
        source.statut = "digested"

    db.commit()
    db.refresh(article)
    return article
