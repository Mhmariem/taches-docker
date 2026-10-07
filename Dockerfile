# Image officielle, tag figé (version exacte de Python + variante + version de Debian).
FROM python:3.13.7-bookworm

# Pas de fichiers .pyc dans l'image, et des logs affichés tout de suite par `docker compose logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Utilisateur sans privilèges : l'application ne tourne pas en root.
RUN useradd --create-home --uid 1000 appuser

# 1) Les dépendances d'abord : cette couche n'est reconstruite que si requirements.txt change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Le code ensuite : c'est ce qui change le plus souvent, donc la dernière couche copiée.
COPY src/ ./src/

USER appuser

EXPOSE 8000

# Forme exec (tableau JSON) : uvicorn est le PID 1 et reçoit directement le SIGTERM de `docker compose stop`.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
