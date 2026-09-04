"""Fixtures partagées par les tests : base SQLite isolée + client HTTP.

Aucun test qui utilise ``client`` (ou ``test_db``) ne touche à la vraie base
de dev (``data/second_brain.db``) : ``get_db`` — la dépendance utilisée par
les routes — est remplacée par une version qui ouvre une session sur une
base SQLite en mémoire, neuve à chaque test.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def test_db():
    """Base SQLite en mémoire, neuve à chaque test, branchée à la place de la vraie base.

    ``sqlite://`` + ``poolclass=StaticPool`` : une base SQLite en mémoire
    ouvre normalement une base *différente* à chaque connexion. StaticPool
    force toutes les sessions à réutiliser la même connexion, donc à voir la
    même base — indispensable ici, sinon chaque session verrait une base vide.

    Yield la fabrique de sessions (``TestingSessionLocal``) : un test peut
    l'appeler pour ouvrir une session et vérifier directement l'état de la base.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Tant que cette surcharge est en place, toute route qui déclare
    # ``db: Session = Depends(get_db)`` reçoit une session sur CETTE base.
    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    # Nettoyage : on ne laisse pas la surcharge ou la base fuiter sur le test suivant.
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(test_db):
    """Client de test HTTP, avec le cycle de vie complet de l'application.

    Dépend de ``test_db`` pour que la surcharge de ``get_db`` soit déjà en
    place avant que l'app démarre. ``with`` déclenche le ``lifespan`` de
    ``app/main.py`` (startup/shutdown) — sans ``with``, ces événements ne se
    déclenchent pas (voir tests/test_health.py, qui fait ce choix inverse).
    """
    with TestClient(app) as c:
        yield c
