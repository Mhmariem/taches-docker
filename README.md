# Gestion de tâches

Application web de gestion de tâches (créer, lister, marquer comme faite) : une API FastAPI avec une page HTML, une base PostgreSQL et l'interface d'administration Adminer, le tout démarré par Docker Compose.

## Prérequis

* Docker Engine 24 ou plus récent
* Docker Compose v2 (2.20 ou plus récent), fourni avec Docker Desktop

Vérification : `docker --version` et `docker compose version`.

## Démarrage

```bash
git clone git push -u origin main
cd taches-docker
cp .env.example .env
docker compose up -d --build
```

Le premier démarrage télécharge les images et construit celle de l'application. `docker compose ps` doit ensuite afficher trois services, dont `db` à l'état `healthy`.

## Accès

|Quoi|URL|
|-|-|
|Application (page web)|http://localhost:8000|
|Documentation interactive de l'API|http://localhost:8000/docs|
|Adminer (administration de la base)|http://localhost:8081|

Connexion dans Adminer : système `PostgreSQL`, serveur `db`, puis l'utilisateur, le mot de passe et la base définis dans `.env`.

La base PostgreSQL n'est volontairement pas publiée sur l'hôte : elle n'est joignable que par les autres services, sous le nom `db`.

## Variables d'environnement

Elles sont lues dans le fichier `.env`, à créer à partir de `.env.example`.

|Variable|Rôle|Valeur d'exemple|
|-|-|-|
|`POSTGRES\_DB`|Nom de la base créée au premier démarrage|`taches`|
|`POSTGRES\_USER`|Utilisateur PostgreSQL utilisé par l'application|`taches`|
|`POSTGRES\_PASSWORD`|Mot de passe de cet utilisateur|`changez-moi`|
|`WEB\_PORT`|Port de l'application sur l'hôte (8000 par défaut)|`8000`|
|`ADMINER\_PORT`|Port d'Adminer sur l'hôte (8080 par défaut)|`8081`|

Les trois variables `POSTGRES\_\*` ne sont prises en compte qu'à la création de la base. Pour les changer ensuite, il faut repartir d'un volume vide (`docker compose down -v`).

## Commandes utiles

```bash
docker compose logs -f web          # suivre les logs de l'application
docker compose exec web bash        # ouvrir un shell dans le conteneur de l'application
docker compose exec db sh -c 'psql -U "$POSTGRES\_USER" -d "$POSTGRES\_DB"'   # ouvrir psql dans la base
docker compose down                 # tout arrêter, les données sont conservées
docker compose down -v              # tout arrêter ET supprimer les données
```

## API

|Méthode|Route|Effet|
|-|-|-|
|`GET`|`/api/taches`|Lister les tâches|
|`POST`|`/api/taches`|Créer une tâche, corps `{"titre": "..."}`|
|`PATCH`|`/api/taches/{id}/faite`|Marquer une tâche comme faite|
|`GET`|`/sante`|Vérifier que l'application joint sa base|



