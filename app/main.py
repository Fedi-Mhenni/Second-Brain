from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routes import articles, capture, folders, sources, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # ``yield`` sans valeur : on rend la main à FastAPI, qui sert les requêtes tant que l'application tourne
    yield


# ``lifespan=lifespan`` : on branche le gestionnaire ci-dessus sur l'application.
app = FastAPI(title="Second Brain", lifespan=lifespan)

# Jinja2Templates est un simple objet de rendu (pas une sous-application
# ASGI) : il n'y a rien à "monter", juste une instance à partager. Elle est
# posée sur ``app.state`` — le mécanisme standard FastAPI/Starlette pour
# exposer un singleton à l'échelle de l'application — plutôt que créée
# directement dans app/routes/web.py ou importée depuis main.py : les deux
# alternatives forceraient soit une deuxième instance (donc un risque de
# configuration qui diverge si on ajoute des filtres Jinja plus tard), soit
# un import circulaire (main.py importe déjà web.py pour brancher son
# router). Les routes y accèdent via ``request.app.state.templates``
# (voir ``app/routes/web.py``).
app.state.templates = Jinja2Templates(directory="app/templates")

# StaticFiles, à l'inverse, EST une sous-application ASGI : il faut la
# monter avec ``app.mount()`` sur un préfixe d'URL (/static) pour qu'elle
# prenne la main sur les requêtes de ce préfixe et serve les fichiers du
# dossier app/static/ (ici, la feuille de style unique demandée).
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Branche les routes de capture (POST /capture/url, POST /capture/note — API JSON)
# et les routes web (dashboard, formulaire, liste des sources — HTML).
app.include_router(capture.router)
app.include_router(web.router)

# Branche la route de listing des dossiers (GET /folders).
app.include_router(folders.router)

# Branche les routes des sources (GET /sources, PATCH /sources/{id}/folder,
# POST /sources/{id}/digest[/auto], POST /sources/{id}/qualification).
app.include_router(sources.router)

# Branche la route de republication (POST /articles/{id}/republications).
app.include_router(articles.router)


@app.get("/health")
def health():
    """Vérification de santé de l'application (utilisée par les tests)."""
    return {"message": "Second Brain is running"}
