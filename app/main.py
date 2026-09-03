from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # ``yield`` sans valeur : on rend la main à FastAPI, qui sert les requêtes tant que l'application tourne
    yield


# ``lifespan=lifespan`` : on branche le gestionnaire ci-dessus sur l'application.
app = FastAPI(title="Second Brain", lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "Second Brain is running"}
