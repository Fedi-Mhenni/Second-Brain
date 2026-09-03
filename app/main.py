from fastapi import FastAPI

app = FastAPI(title="Second Brain")


@app.get("/")
def home():
    return {"message": "Second Brain is running"}