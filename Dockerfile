FROM python:3.12-slim

WORKDIR /app

# Dépendances prod (requirements.txt) + dev/tests (requirements-dev.txt).
# Copiées avant le code pour profiter du cache de couches Docker.
COPY requirements.txt requirements-dev.txt ./

# On installe les deux : l'image peut ainsi lancer l'app ET pytest, sans étape manuelle.
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
