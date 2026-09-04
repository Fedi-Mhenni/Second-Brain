from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routes import capture, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # ``yield`` sans valeur : on rend la main à FastAPI, qui sert les requêtes tant que l'application tourne
    yield


# ``lifespan=lifespan`` : on branche le gestionnaire ci-dessus sur l'application.
app = FastAPI(title="Second Brain", lifespan=lifespan)

# Rendu Jinja2, exposé aux routes via ``request.app.state.templates``
# (voir ``app/routes/web.py``) pour éviter tout import circulaire avec main.py.
app.state.templates = Jinja2Templates(directory="app/templates")

# Fichiers statiques (CSS) servis sous /static.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Branche les routes de capture (POST /capture/url, POST /capture/note — API JSON)
# et les routes web (dashboard, formulaire, liste des sources — HTML).
app.include_router(capture.router)
app.include_router(web.router)


@app.get("/health")
def health():
    """Vérification de santé de l'application (utilisée par les tests)."""
    return {"message": "Second Brain is running"}
