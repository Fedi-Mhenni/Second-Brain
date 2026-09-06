"""Service de l'étape « Qualifier ».

Deux points d'entrée :
- ``qualifier_source``      : upsert manuel de la Qualification ; l'appelant
  fournit categorie/legitimite/interet/qualified_by.
- ``qualifier_source_auto`` : ces trois premiers champs sont déduits par un
  ``LLMProvider`` à partir du titre/contenu de la Source, puis réutilise
  ``qualifier_source`` avec ``qualified_by="ai"``.
"""

import json
import re

from sqlalchemy.orm import Session

from app.models import Qualification, Source
from app.models.qualification import CATEGORIES
from app.models.source import avancer_statut
from app.services.llm_provider import get_llm_provider
from app.services.ranger import SourceIntrouvable

# Balises markdown (```json ... ```) que certains modèles ajoutent autour
# d'une réponse JSON malgré la consigne : on les retire avant de parser.
_BALISES_MARKDOWN = re.compile(r"^```(?:json)?\s*|\s*```$")

# Longueur de contenu conservée dans le prompt : au-delà, ça n'aide pas la
# qualification et ça alourdit inutilement l'appel au modèle.
_MAX_CONTENU_PROMPT = 4_000


def qualifier_source(
    db: Session,
    source_id: int,
    categorie: str | None,
    legitimite: int | None,
    interet: int | None,
    qualified_by: str,
) -> Qualification:
    """Crée ou met à jour la Qualification liée à ``source_id``.

    ``categorie``/``legitimite``/``interet`` acceptent ``None`` : une
    qualification automatique (voir ``qualifier_source_auto``) peut ne pas
    avoir pu déduire l'un de ces champs depuis la réponse du modèle ; la
    colonne correspondante l'autorise déjà (``CheckConstraint`` sur
    ``Qualification``, voir app/models/qualification.py).

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

    # Règle d'avancement commune aux trois services (Ranger/Qualifier/Digérer) :
    # voir avancer_statut (app/models/source.py).
    avancer_statut(source, "qualified")

    db.commit()
    db.refresh(qualification)
    return qualification


def _construire_prompt(titre: str | None, contenu: str | None) -> str:
    """Construit le prompt de qualification envoyé au modèle.

    Demande explicitement un JSON strict, sans balises ni texte autour :
    ``_parser_reponse`` doit rester simple, la contrainte de format est
    posée ici plutôt que compensée par un parsing plus complexe.
    """
    contenu_tronque = (contenu or "")[:_MAX_CONTENU_PROMPT]
    return (
        "Tu es un assistant qui évalue une source de veille personnelle pour "
        "aider à la classer.\n\n"
        f"Titre : {titre or '(sans titre)'}\n"
        f"Contenu : {contenu_tronque or '(aucun contenu extrait)'}\n\n"
        "Réponds UNIQUEMENT avec un objet JSON strict, sans texte avant ni "
        "après, sans balises markdown, au format exact suivant :\n"
        '{"categorie": "...", "legitimite": ..., "interet": ...}\n\n'
        "Contraintes :\n"
        "- \"categorie\" doit être exactement l'une de ces valeurs : "
        "metier, pro, perso, culture\n"
        "- \"legitimite\" est un entier entre 1 et 5 : à quel point la "
        "source semble fiable et sérieuse\n"
        "- \"interet\" est un entier entre 1 et 5 : à quel point le "
        "contenu est intéressant à retravailler\n\n"
        "N'ajoute aucune explication, aucun texte hors de l'objet JSON."
    )


def _valider_note(valeur) -> int | None:
    """Convertit ``valeur`` en entier 1-5, ou ``None`` si ce n'est pas possible."""
    try:
        note = int(valeur)
    except (TypeError, ValueError):
        return None
    return note if 1 <= note <= 5 else None


def _parser_reponse(texte: str) -> tuple[str | None, int | None, int | None]:
    """Extrait ``(categorie, legitimite, interet)`` d'une réponse IA, sans jamais lever.

    La réponse est censée être un objet JSON strict (voir ``_construire_prompt``),
    mais les modèles entourent parfois leur JSON de balises markdown
    (```json ... ```), ou renvoient un texte qui n'est pas du JSON valide, ou
    des valeurs hors des bornes attendues, ou omettent un champ. Dans tous ces
    cas, le champ concerné est mis à ``None`` plutôt que de faire planter la
    qualification : ``qualifier_source`` accepte ``None`` sur ces trois
    champs (voir plus haut) et la Qualification est tout de même créée avec
    ce qui a pu être extrait, quitte à être complétée à la main ensuite.
    """
    texte_nettoye = _BALISES_MARKDOWN.sub("", texte.strip())

    try:
        donnees = json.loads(texte_nettoye)
    except (json.JSONDecodeError, TypeError):
        return None, None, None

    if not isinstance(donnees, dict):
        return None, None, None

    categorie = donnees.get("categorie")
    if categorie not in CATEGORIES:
        categorie = None

    return categorie, _valider_note(donnees.get("legitimite")), _valider_note(donnees.get("interet"))


def qualifier_source_auto(db: Session, source_id: int) -> tuple[Qualification, str]:
    """Qualifie automatiquement une Source via le ``LLMProvider`` courant.

    Ne recalcule ni l'upsert ni l'avancement de statut : déduit seulement
    ``categorie``/``legitimite``/``interet`` de la réponse du modèle, puis
    délègue entièrement à ``qualifier_source`` avec ``qualified_by="ai"``.

    Retourne ``(qualification, nom_du_provider)`` — même convention que
    ``digerer_source_auto`` (voir app/services/digerer.py).

    Lève ``SourceIntrouvable`` si la Source n'existe pas. Ne lève jamais à
    cause d'une réponse IA malformée (voir ``_parser_reponse``).
    """
    source = db.get(Source, source_id)
    if source is None:
        raise SourceIntrouvable(source_id)

    provider = get_llm_provider()
    prompt = _construire_prompt(source.titre, source.contenu_brut)
    reponse = provider.generer(prompt)

    categorie, legitimite, interet = _parser_reponse(reponse)

    qualification = qualifier_source(
        db,
        source_id,
        categorie=categorie,
        legitimite=legitimite,
        interet=interet,
        qualified_by="ai",
    )
    return qualification, type(provider).__name__
