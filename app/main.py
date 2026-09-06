from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import capture, folders, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # ``yield`` sans valeur : on rend la main à FastAPI, qui sert les requêtes tant que l'application tourne
    yield


# ``lifespan=lifespan`` : on branche le gestionnaire ci-dessus sur l'application.
app = FastAPI(title="Second Brain", lifespan=lifespan)

# Branche les routes de capture (POST /capture/url).
app.include_router(capture.router)

# Branche la route de listing des dossiers (GET /folders).
app.include_router(folders.router)

# Branche la route de listing des sources (GET /sources).
app.include_router(sources.router)


@app.get("/")
def home():
    return {"message": "Second Brain is running"}
