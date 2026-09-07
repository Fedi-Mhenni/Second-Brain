"""Point d'entrée pour le déploiement Vercel.

Vercel (runtime @vercel/python) cherche une variable ``app`` compatible ASGI
dans ce fichier — exactement ce que FastAPI expose déjà dans ``app/main.py``.
Ce fichier ne fait que ré-exporter cette même instance : aucune logique
dupliquée, un seul FastAPI() pour tout le projet.
"""

from app.main import app  # noqa: F401  (réexporté pour Vercel)
