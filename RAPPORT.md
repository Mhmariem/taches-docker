# RAPPORT — mini-projet Docker

- **Dépôt** : https://github.com/Mhmariem/taches-docker
- **Application** : gestion de tâches (option B). Trois services : `web` (FastAPI, construit par le Dockerfile), `db` (PostgreSQL 17) et `adminer`.
- **Machine de mesure** : PC sous Windows, Docker 29.5.3 (Docker Desktop), Docker Compose v5.1.4. Toutes les mesures ci-dessous ont été prises sur cette machine.

## 1. Image de base

J'ai retenu `python:3.13.7-slim-bookworm` : image officielle, tag figé sur la version exacte de Python, la variante et la version de Debian.

- **Pas la variante complète** (`python:3.13.7-bookworm`). Elle embarque les compilateurs et les en-têtes de développement. Mon application n'en a pas besoin : ses trois dépendances s'installent sous forme de paquets précompilés (wheels), y compris le pilote PostgreSQL grâce à `psycopg[binary]`. Je l'ai mesuré : l'image passe de 1,53 Go à 233 Mo (voir question 3).
- **Pas alpine.** Alpine utilise la bibliothèque C `musl` au lieu de `glibc`. Les wheels Python sont d'abord construits et testés pour `glibc` ; sur alpine, un paquet sans wheel `musl` doit être compilé dans l'image, ce qui oblige à installer `gcc` et annule le gain.

## 2. Cache

Les instructions vont de la plus stable à la plus volatile :

```dockerfile
FROM python:3.13.7-slim-bookworm          # change à chaque montée de version de Python
ENV ... / WORKDIR /app / RUN useradd ...  # ne change presque jamais
COPY requirements.txt .                   # change quand j'ajoute une dépendance
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/                          # change à chaque modification du code
USER appuser / EXPOSE 8000 / CMD [...]    # métadonnées, sans coût
```

Docker réutilise une couche tant que l'instruction et les fichiers qu'elle copie sont identiques, et reconstruit tout ce qui suit la première couche modifiée. Les dépendances sont donc copiées et installées **avant** le code : modifier le code ne les invalide pas. Avec un `COPY . .` placé avant `pip install`, la moindre modification relancerait l'installation.

Deux builds successifs : `docker compose build --no-cache web`, puis `docker compose build web` après avoir modifié une ligne de `src/main.py`.

| Étape | Build 1 : `--no-cache` | Build 2 : après modification du code |
| --- | --- | --- |
| load metadata (image de base) | 2,1 s | 11,4 s |
| [2/6] `WORKDIR /app` | CACHED | CACHED |
| [3/6] `RUN useradd` | 0,5 s | CACHED |
| [4/6] `COPY requirements.txt .` | 0,1 s | CACHED |
| [5/6] `RUN pip install` | 18,9 s | CACHED |
| [6/6] `COPY src/ ./src/` | 0,1 s | 0,0 s (refaite) |
| exporting to image | 2,7 s | 0,9 s |
| **Durée totale affichée** | **25,3 s** | **13,3 s** |

Extrait de la sortie du build 2 :

```text
#8 [4/6] COPY requirements.txt .
#8 CACHED
#10 [5/6] RUN pip install --no-cache-dir -r requirements.txt
#10 CACHED
#11 [6/6] COPY src/ ./src/
#11 DONE 0.0s
 ✔ Image taches-web Built                                              13.3s
```

Lecture :

- Au build 2, seule l'étape `COPY src/ ./src/` est réexécutée. `pip install`, qui coûtait 18,9 s, reste `CACHED`.
- Les 13,3 s du build 2 ne sont pas du temps de construction : 11,4 s viennent de l'interrogation du registre pour l'image de base (réseau). Hors cette étape, on passe de 23,2 s à 1,9 s.
- Le tout premier build, sans rien en local, avait duré 242,8 s, dont 160 s de téléchargement de l'image de base et 62,1 s de `pip install`.

## 3. Taille

Sortie de `docker image ls taches-web` :

```text
IMAGE                 ID             DISK USAGE   CONTENT SIZE
taches-web:complete   e476851c09e0       1.53GB          393MB
taches-web:latest     3b6c5655f2f7        233MB         55.4MB
```

Avec la variante `slim`, l'image passe de 1,53 Go à 233 Mo sur disque (de 393 Mo à 55,4 Mo compressée) : elle est 6,6 fois plus petite, soit 85 % de moins. Pour obtenir la valeur « avant », j'ai construit la même application avec `docker build -t taches-web:complete .` en changeant uniquement la ligne `FROM` : le gain vient donc entièrement du choix de la variante `slim`. Deux autres choix évitent de grossir l'image : `pip install --no-cache-dir`, qui ne garde pas les archives téléchargées dans la couche, et le `.dockerignore`, qui laisse hors de l'image `.git`, `.env`, les caches Python et la documentation.

## 4. Persistance

Les données de PostgreSQL sont dans le volume nommé `db_data`, monté sur `/var/lib/postgresql/data`, le répertoire de données (`PGDATA`) de l'image `postgres:17`. Compose le préfixe du nom du projet : il s'appelle `taches_db_data`.

- **`docker compose restart`** : les conteneurs sont arrêtés puis relancés, sans être recréés. Rien ne bouge.
- **`docker compose down` puis `up`** : `down` supprime les trois conteneurs et le réseau, mais pas le volume. `up` crée des conteneurs neufs et rebranche le même volume. PostgreSQL trouve un répertoire de données déjà initialisé : il ne rejoue pas l'initialisation et ignore `POSTGRES_USER`, `POSTGRES_PASSWORD` et `POSTGRES_DB`. L'application exécute `CREATE TABLE IF NOT EXISTS`, qui ne fait rien. Les tâches sont conservées.
- **`docker compose down -v`** : le volume est supprimé avec les conteneurs. Au `up` suivant, Compose crée un volume vide, PostgreSQL réinitialise la base, l'application recrée la table. La liste est vide.

Ce que j'ai observé dans les sorties, ici après `down -v` :

```text
> docker compose down -v
 ✔ Network taches_default     Removed
 ✔ Volume taches_db_data      Removed
> docker compose up -d
 ✔ Network taches_default     Created
 ✔ Volume taches_db_data      Created
```

Le `down` simple, lui, n'a listé que les trois conteneurs et le réseau : le volume n'y apparaît pas, et le `up` suivant ne l'a pas recréé. Sans la ligne `volumes:`, les données vivraient dans la couche d'écriture du conteneur et disparaîtraient dès le premier `down`. Le chemin dépend de la version : à partir de `postgres:18`, l'image attend le volume sur `/var/lib/postgresql`.

## 5. Difficulté

Deux obstacles rapides d'abord : `cp` n'existe pas dans l'invite de commandes Windows (remplacé par `copy`), puis `failed to connect to the docker API` parce que Docker Desktop n'était pas démarré.

Le vrai blocage a été la publication du port d'Adminer. Au premier `docker compose up -d --build`, `db` était `Healthy` et `web` `Started`, mais pas `adminer` :

```text
Error response from daemon: ports are not available: exposing port TCP 127.0.0.1:8080 -> 127.0.0.1:0: listen tcp4 127.0.0.1:8080: bind: An attempt was made to access a socket in a way forbidden by its access permissions.
```

**Diagnostic.** Le message vient du démon Docker, pas d'Adminer : le conteneur n'a même pas démarré. Les deux autres services tournaient, donc ni les images ni le réseau Compose n'étaient en cause : c'est la machine hôte qui refusait l'écoute sur le port 8080.

**Correction.** Le port est une variable. J'ai voulu passer `ADMINER_PORT` à 8081 et j'ai relancé : même erreur, toujours sur 8080. `type .env` m'a montré que le fichier contenait encore `ADMINER_PORT=8080` : ma modification n'avait pas été enregistrée dans `.env`. Après correction avec `notepad .env`, `docker compose up -d` a démarré Adminer, et `docker compose ps` l'a confirmé :

```text
taches-adminer-1   adminer:5.3.0   ...   127.0.0.1:8081->8080/tcp
```

**Ce que j'en retiens.** Publier un port engage la machine hôte, pas seulement le conteneur : c'est pour cela que les ports sont des variables et non des valeurs en dur dans `compose.yaml`. J'ai ensuite mis 8081 par défaut dans `.env.example`, `compose.yaml` et le README, pour qu'un correcteur sous Windows ne rencontre pas la même erreur. Et avant de relancer, `type .env` ou `docker compose config` montrent la configuration réellement utilisée.
