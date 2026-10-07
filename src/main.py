"""Gestion de tâches : créer une tâche, lister les tâches, marquer une tâche comme faite. Test du cache"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from psycopg.rows import dict_row
from pydantic import BaseModel

# Paramètres de connexion lus dans l'environnement (fournis par compose.yaml).
# DB_HOST vaut "db" : le NOM du service Compose, jamais une adresse IP ni localhost.
DB = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
}

PAGE = Path(__file__).parent / "static" / "index.html"


def connexion():
    """Ouvre une connexion ; les lignes sont renvoyées sous forme de dictionnaires."""
    return psycopg.connect(**DB, row_factory=dict_row)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Exécuté une fois au démarrage : crée la table si elle n'existe pas encore.
    with connexion() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS taches (
                id       SERIAL PRIMARY KEY,
                titre    TEXT NOT NULL,
                faite    BOOLEAN NOT NULL DEFAULT FALSE,
                creee_le TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    yield


app = FastAPI(title="Gestion de tâches", lifespan=lifespan)


class NouvelleTache(BaseModel):
    titre: str


@app.get("/", include_in_schema=False)
def page_accueil():
    """Page HTML accessible depuis le navigateur de l'hôte."""
    return FileResponse(PAGE)


@app.get("/api/taches")
def lister_taches():
    with connexion() as conn:
        return conn.execute(
            "SELECT id, titre, faite, creee_le FROM taches ORDER BY id"
        ).fetchall()


@app.post("/api/taches", status_code=201)
def creer_tache(tache: NouvelleTache):
    titre = tache.titre.strip()
    if not titre:
        raise HTTPException(status_code=422, detail="Le titre ne peut pas être vide.")
    with connexion() as conn:
        return conn.execute(
            "INSERT INTO taches (titre) VALUES (%s) RETURNING id, titre, faite, creee_le",
            (titre,),
        ).fetchone()


@app.patch("/api/taches/{tache_id}/faite")
def marquer_faite(tache_id: int):
    with connexion() as conn:
        tache = conn.execute(
            "UPDATE taches SET faite = TRUE WHERE id = %s RETURNING id, titre, faite, creee_le",
            (tache_id,),
        ).fetchone()
    if tache is None:
        raise HTTPException(status_code=404, detail="Tâche introuvable.")
    return tache


@app.get("/sante")
def sante():
    """Vérifie que l'application joint bien sa base."""
    with connexion() as conn:
        conn.execute("SELECT 1")
    return {"statut": "ok", "base": DB["host"]}
