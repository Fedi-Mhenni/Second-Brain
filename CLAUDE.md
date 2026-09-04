# Règles de travail — Second Cerveau

## Méthode
- Une brique à la fois. Ne pas anticiper les briques suivantes.
- Expliquer l'approche avant d'écrire le code, et attendre ma validation.
- Ne rien ajouter qui n'a pas été demandé. Si un ajout semble nécessaire,
  le proposer et attendre ma réponse.
- Lire docs/CADRAGE.md au début de chaque session.

## Stack imposée (décisions actées, ne pas changer sans accord du binôme)
FastAPI, SQLAlchemy, SQLite, Jinja2 server-rendered, Docker.
LLM appelé en HTTP direct avec httpx, derrière une abstraction LLMProvider
avec repli automatique sur un MockProvider.
Interdits : authentification, comptes utilisateurs, PostgreSQL, framework
front (React/Vue), SDK éditeur, scheduler applicatif, API d'auto-publication
LinkedIn ou X.

## Architecture
- app/models/    un fichier par entité
- app/routes/    endpoints FastAPI, appellent les services, jamais de logique métier
- app/services/  toute la logique métier
- app/templates/ Jinja2

## Git
- Config pure : commit direct sur main.
- Code métier : branche feature/nom-de-la-brique, petits commits, PR vers main.
- Ne jamais commiter .env, *.db, __pycache__/, venv/

## Code
- Commentaires en français sur les lignes Python non triviales.
- Gérer explicitement les cas d'échec, jamais de plantage silencieux.
