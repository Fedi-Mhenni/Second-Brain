"""Test de santé : l'application répond sur /health.

Lancement : ``python -m pytest`` depuis la racine du projet (le ``-m`` place la
racine sur le ``sys.path``, ce qui permet le ``from app.main import app``).
"""

from fastapi.testclient import TestClient

from app.main import app

# ``TestClient`` sans bloc ``with`` : les événements de démarrage (lifespan) ne
# se déclenchent pas, donc ``init_db()`` n'est pas appelé et aucune base n'est
# créée par ce test.
client = TestClient(app)


def test_health_ok():
    # ``/`` sert désormais le dashboard HTML (voir app/routes/web.py) ; le
    # health-check JSON est passé sur /health.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"message": "Second Brain is running"}
