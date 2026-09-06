"""Modèle ``Source`` : une ressource captée (une URL) et son avancement dans le workflow.

Workflow : Capter -> Qualifier -> Ranger -> Digérer -> Republier.
Chaque étape se traduit par une valeur de ``statut`` sur la Source.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base, utcnow

# Les cinq états possibles d'une Source, dans l'ordre du workflow.
# On stocke la valeur en texte ; cette constante sert de référence pour la
# validation, qui se fera dans la couche service (pas dans le modèle).
STATUTS = ("captured", "qualified", "ranged", "digested", "published")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)

    # L'URL captée, pour une Source issue d'une page web.
    # ``nullable=True`` : une note libre (POST /api/capture/note) n'a pas d'URL.
    # ``unique=True``  : jamais deux fois la même URL ; plusieurs NULL restent permis
    #                    (SQLite comme PostgreSQL traitent les NULL comme distincts).
    # ``index=True``   : recherche rapide par URL (pour tester si elle existe déjà).
    url = Column(String(2048), unique=True, index=True, nullable=True)

    # Titre de la page, récupéré lors du fetch : inconnu au moment où on colle l'URL.
    titre = Column(String(512), nullable=True)

    # Texte brut extrait de la page. ``Text`` (et non ``String``) car potentiellement long.
    contenu_brut = Column(Text, nullable=True)

    # Étape courante dans le workflow. Voir la constante STATUTS ci-dessus.
    # ``default="captured"`` : une Source naît toujours à l'étape « captée ».
    statut = Column(String(20), nullable=False, default="captured")

    # Dossier de rangement (étape 3) : nul tant que la source n'est pas rangée.
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)

    # Suivi temporel. ``default`` est appelé à la création, ``onupdate`` à chaque
    # modification de la ligne. On passe la fonction ``utcnow`` (sans parenthèses) :
    # SQLAlchemy l'appellera lui-même au bon moment.
    # ``DateTime(timezone=True)`` : la colonne garde le fuseau (les valeurs de
    # ``utcnow`` sont en UTC) ; portable vers un SGBD qui gère les timestamps avec fuseau.
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relation un-à-un vers l'Article issu de cette Source.
    # ``uselist=False`` : ``source.article`` renvoie un seul objet (ou None), pas une liste.
    # ``back_populates`` : tient les deux côtés de la relation synchronisés.
    # La chaîne "Article" évite d'importer la classe ici (résolue par SQLAlchemy).
    article = relationship("Article", back_populates="source", uselist=False)

    # Le dossier où la Source est rangée (None tant qu'elle ne l'est pas).
    folder = relationship("Folder", back_populates="sources")

    # Relation un-à-un vers la Qualification de cette Source (étape Qualifier).
    # ``uselist=False`` car Qualification.source_id est unique (voir ce modèle) :
    # même raison que pour ``article`` ci-dessus.
    qualification = relationship(
        "Qualification", back_populates="source", uselist=False
    )

    def __repr__(self) -> str:
        # Affichage lisible dans les logs et le shell Python. ``!r`` = repr de la valeur.
        return f"<Source id={self.id} statut={self.statut!r} url={self.url!r}>"
