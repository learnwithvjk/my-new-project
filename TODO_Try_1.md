Absolutely — this is a fantastic way to learn Docker! Below is a **complete, step-by-step, implementation-first learning path**. By the end, you’ll have **two (or more) applications running in multiple Docker containers**, all on the **same Docker network**, able to **communicate with each other (inter-container)**, **communicate internally**, and also able to **read/write files from the host** and be **accessed from the host**.

I’ve ordered it so each step builds on the previous one, with concrete commands and small projects you’ll actually build (no “magic”, you’ll implement everything).

---

## 🧭 Learning goal (end state)
- ✅ Docker installed and verified  
- ✅ You can build custom Docker images from Dockerfiles  
- ✅ You run **≥ 2 containers** (e.g., `api` + `web` + optionally `db`)  
- ✅ All containers run on the **same user-defined Docker network**  
- ✅ **Inter-container communication** works (container → container by service/container name DNS)  
- ✅ **Intra-container** behavior understood (processes, ports, filesystem)  
- ✅ **Host ↔ container communication** works (publish ports + bind mounts/volumes to read/write host files)  
- ✅ Everything is reproducible via Docker CLI (and optionally `docker compose`)

---

## 🧰 Step 1) Install Docker + verify your environment (10–15 min)

1. **Install Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux): https://docs.docker.com/get-docker/  
2. Confirm it works:
   ```bash
   docker --version
   docker run --rm hello-world
   ```
3. (Recommended) Enable buildx & compose (usually preinstalled):
   ```bash
   docker buildx version
   docker compose version   # or: docker-compose version
   ```
4. Create a working folder:
   ```bash
   mkdir ~/docker-learning && cd ~/docker-learning
   ```

---

## 🧩 Step 2) Learn the core Docker concepts by using them (15–20 min)

Run these *to feel* images/containers/networks/volumes:

1. **List images/containers/networks/volumes**:
   ```bash
   docker images
   docker ps -a
   docker network ls
   docker volume ls
   ```
2. **Run an interactive container** (great for “it’s just a process + filesystem”):
   ```bash
   docker run --rm -it alpine sh
   # inside: apk add curl; curl -I https://example.com; exit
   ```
3. **Understand isolation vs sharing**: run two containers and see they don’t share files unless you mount something.

---

## 🏗️ Step 3) Build your first custom image (Dockerfile fundamentals) (20–30 min)

Create a tiny “hello API” with Python/Flask.

1. Make app folder:
   ```bash
   mkdir -p apps/api && cd apps/api
   ```
2. Create `app.py`:
   ```python
   from flask import Flask, jsonify, request
   app = Flask(__name__)

   @app.get("/health")
   def health():
       return jsonify(status="ok")

   @app.get("/hello")
   def hello():
       name = request.args.get("name", "world")
       return jsonify(message=f"hello, {name}")

   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=5012)
   ```
3. Create `requirements.txt`:
   ```
   flask==3.0.3
   ```
4. Create `Dockerfile`:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY app.py .
   EXPOSE 5012
   CMD ["python", "app.py"]
   ```
5. Build + run:
   ```bash
   docker build -t learn_docker/api:1.0 ./apps/api
   docker run --rm -p 5012:5012 --name api learn_docker/api:1.0
   ```
6. From **host**, test:
   - http://localhost:5012/health  
   - http://localhost:5012/hello?name=alice

✅ You now have: a custom image + a running container + host→container access via published port.

---

## 🌐 Step 4) Create a dedicated Docker network (so containers resolve each other by name) (10 min)

1. Create a user-defined bridge network:
   ```bash
   docker network create appnet
   docker network ls
   ```
2. Run `api` attached to that network (stop the previous one first: `Ctrl+C`):
   ```bash
   docker run --rm -d --name api --network appnet -p 5012:5012 learn_docker/api:1.0
   docker ps
   ```
3. Validate DNS resolution *inside* Docker network by starting a helper container:
   ```bash
   docker run --rm -it --network appnet alpine sh -c "apk add curl && curl -s http://api:5012/health"
   ```
   ✅ This proves **inter-container communication** using container name `api`.

---

## 🧱 Step 5) Build a second application (web/frontend) that calls the API (inter-container communication) (30–45 min)

Let’s build a tiny web app (Python/Flask) that calls the API by its container name.

1. Create folder:
   ```bash
   mkdir -p ./apps/web && cd ./apps/web
   ```
2. `app.py`:
   ```python
   from flask import Flask, render_template_string, request
   import os, requests

   app = Flask(__name__)
   API_URL = os.getenv("API_URL", "http://api:5012")

   TEMPLATE = """
   <html><body>
   <h1>Web → API demo</h1>
   <form method="get">
     <input name="name" placeholder="your name" value="{{name}}"/>
     <button>Say hello</button>
   </form>
   <pre>{{result}}</pre>
   </body></html>
   """

   @app.get("/")
   def index():
       name = request.args.get("name", "docker learner")
       try:
           r = requests.get(f"{API_URL}/hello", params={"name": name}, timeout=3)
           r.raise_for_status()
           result = r.json()
       except Exception as e:
           result = {"error": str(e)}
       return render_template_string(TEMPLATE, name=name, result=result)

   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=8080)
   ```
3. `requirements.txt`:
   ```
   flask==3.0.3
   requests==2.32.3
   ```
4. `Dockerfile`:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY app.py .
   EXPOSE 8080
   CMD ["python", "app.py"]
   ```
5. Build:
   ```bash
   docker build -t learn_docker/web:1.0 ./apps/web
   ```
6. Run on the **same network**, passing `API_URL` env var (optional if default matches):
   ```bash
   docker run --rm -d --name web --network appnet -p 8080:8080 -e API_URL=http://api:5012 learn_docker/web:1.0
   ```
7. From **host**, open: http://localhost:8080/  
   ✅ You should see the web calling the API via `http://api:5012` (inter-container DNS). Try changing the name.

**At this point you have 2 containers (api + web) on the same network, communicating with each other.**

---

## 📂 Step 6) Host ↔ container communication: read/write files using bind mounts (20–30 min)

Let’s make the API read a config/message from the **host**, and also write logs to the **host**.

1. On host, create shared folder + files:
   ```bash
   mkdir -p ./shared
   echo "Hello from HOST config" >> ./shared/message.txt
   ```
2. Update `apps/api/app.py` to read that file (optional but great demo):
   ```python
   from flask import Flask, jsonify, request
   from pathlib import Path

   app = Flask(__name__)
   MESSAGE_FILE = Path("/data/message.txt")

   @app.get("/health")
   def health():
       return jsonify(status="ok")

   @app.get("/hello")
   def hello():
       name = request.args.get("name", "world")
       try:
           msg = MESSAGE_FILE.read_text().strip() if MESSAGE_FILE.exists() else "no host message found"
       except Exception as e:
           msg = f"error reading message: {e}"
       return jsonify(message=f"hello, {name}", from_host=msg)

   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=5012)
   ```
3. Rebuild API image (small change):
   ```bash
   cd ./apps/api
   docker build -t learn_docker/api:1.1 ./apps/api
   ```
4. Run API with a **bind mount** to share host `./shared` into container `/data`:
   ```bash
   docker rm -f api || true
   docker run --rm -d --name api --network appnet -p 5012:5012 \
     -v ./shared:/data:ro \
     learn_docker/api:1.1
   ```
   - `:ro` = read-only (safe). Remove `:ro` if you want container→host writes.
5. Test from host: http://localhost:5012/hello → should include `from_host` from your host file.  
6. (Optional) Demonstrate logs to host by mounting a logs dir:
   ```bash
   mkdir -p ./shared/logs
   docker rm -f api || true
   docker run --rm -d --name api --network appnet -p 5012:5012 \
     -v ./shared:/data:ro \
     -v ./shared/logs:/logs \
     learn_docker/api:1.1
   # inside container you could write /logs/api.log; it appears on host
   ```

✅ Host↔container file communication is now working (read + optional write).

---

## 🧰 Step 7) Add a third component (database) to show full multi-container architecture (30–60 min)

Let’s add **PostgreSQL** and have the API read/write a tiny “visits” table. This is the cleanest way to prove real inter-container service communication + persistence.

1. Start Postgres on the same network, with a named volume for persistence:
   ```bash
   docker volume create pgdata
   docker run --rm -d --name db --network appnet \
     -e POSTGRES_USER=app \
     -e POSTGRES_PASSWORD=app \
     -e POSTGRES_DB=app \
     -v pgdata:/var/lib/postgresql/data \
     postgres:16
   ```
2. (Optional) Verify DB is reachable from another container:
   ```bash
   docker run --rm -it --network appnet postgres:16 \
     psql -h db -U app -d app -c "SELECT now();"
   # password: app
   ```
3. Update API to use Postgres. Add dependency:
   - `apps/api/requirements.txt` append: `psycopg[binary]==3.2.1`
4. Update `apps/api/app.py`:
   ```python
   from flask import Flask, jsonify, request
   from pathlib import Path
   import os, psycopg

   app = Flask(__name__)
   MESSAGE_FILE = Path("/data/message.txt")
   DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")

   def get_conn():
       return psycopg.connect(DATABASE_URL, autocommit=True)

   # ensure table exists
   with get_conn() as conn, conn.cursor() as cur:
       cur.execute("""
         CREATE TABLE IF NOT EXISTS visits (
           id SERIAL PRIMARY KEY,
           name TEXT NOT NULL,
           ts TIMESTAMPTZ DEFAULT now()
         );
       """)

   @app.get("/health")
   def health():
       try:
           with get_conn() as conn, conn.cursor() as cur:
               cur.execute("SELECT 1")
           db_ok = True
       except Exception as e:
           db_ok = False
       return jsonify(status="ok", db_ok=db_ok)

   @app.get("/hello")
   def hello():
       name = request.args.get("name", "world")
       try:
           msg = MESSAGE_FILE.read_text().strip() if MESSAGE_FILE.exists() else "no host message found"
       except Exception as e:
           msg = f"error reading message: {e}"
       # record visit
       try:
           with get_conn() as conn, conn.cursor() as cur:
               cur.execute("INSERT INTO visits(name) VALUES (%s) RETURNING id, ts", (name,))
               vid, ts = cur.fetchone()
       except Exception as e:
           vid, ts = None, str(e)
       return jsonify(message=f"hello, {name}", from_host=msg, visit={"id": vid, "ts": str(ts)})

   @app.get("/visits")
   def visits():
       try:
           with get_conn() as conn, conn.cursor() as cur:
               cur.execute("SELECT id, name, ts FROM visits ORDER BY id DESC LIMIT 50")
               rows = [{"id": r[0], "name": r[1], "ts": str(r[2])} for r in cur.fetchall()]
           return jsonify(rows)
       except Exception as e:
           return jsonify(error=str(e)), 500

   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=5012)
   ```
5. Update requirement.txt :
   
   ```
   flask==3.0.3
   psycopg[binary]==3.1.18
   ```
6. Rebuild API image:
   ```bash
   cd ./apps/api
   docker build -t learn_docker/api:1.2 ./apps/api
   ```
7. Restart API with DB env + (still) bind mount:
   ```bash
   docker rm -f api || true
   docker run -d --name db --network appnet \
      -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=app \
      postgres:16

   docker build -t learn_docker/api:1.2 ./apps/api
   docker run --rm -it --name api --network appnet -p 5012:5012 \
      -e DATABASE_URL=postgresql://app:app@db:5432/app \
      -v ./shared:/data:ro \
      learn_docker/api:1.2
   ```
8. Test:
   - http://localhost:5012/health  → should show `db_ok: true`  
   - http://localhost:5012/hello?name=ada → returns visit info  
   - http://localhost:5012/visits → list recent visits

✅ Now you have **3 containers** (web, api, db) on the same network, full inter-container communication, persistence via volume, and host file access.

---

## 🧪 Step 8) Make everything reproducible + easy with Docker Compose (highly recommended) (15–25 min)

Compose is the clean “implement everything” tool: it declares networks, volumes, env, depends_on, ports, mounts.

1. In `./`, create `docker-compose.yml`:
   ```yaml
   version: "3.9"
   services:
     db:
       image: postgres:16
       container_name: db
       environment:
         POSTGRES_USER: app
         POSTGRES_PASSWORD: app
         POSTGRES_DB: app
       volumes:
         - pgdata:/var/lib/postgresql/data
       networks: [appnet]
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U app -d app"]
         interval: 5s
         timeout: 3s
         retries: 10

     api:
       build: ./apps/api
       container_name: api
       environment:
         DATABASE_URL: postgresql://app:app@db:5432/app
       volumes:
         - ./shared:/data:ro        # host ↔ container files
         - ./shared/logs:/logs      # optional logs to host
       ports:
         - "5012:5012"               # host ↔ container access
       depends_on:
         db:
           condition: service_healthy
       networks: [appnet]
       healthcheck:
         test: ["CMD", "curl", "-fsS", "http://localhost:5012/health"]
         interval: 5s
         timeout: 3s
         retries: 10

     web:
       build: ./apps/web
       container_name: web
       environment:
         API_URL: http://api:5012
       ports:
         - "8080:8080"               # host ↔ container access
       depends_on:
         api:
           condition: service_healthy
       networks: [appnet]

   networks:
     appnet:
       driver: bridge

   volumes:
     pgdata:
   ```
2. Launch the whole stack:
   ```bash
   docker compose up --build -d
   docker compose ps
   docker compose logs -f api web db   # watch startup
   ```
3. Verify end-to-end:
   - http://localhost:8080/  (web → api → db, reads host `/data/message.txt`)  
   - http://localhost:5012/health  
   - http://localhost:5012/visits

4. Tear down / reset:
   ```bash
   docker compose down           # stop stack (keeps pgdata volume)
   docker compose down -v        # stop + remove volume (fresh DB)
   ```

✅ With Compose you now have a **single command** to run 3+ containers, shared network, volumes, bind mounts, healthchecks, dependencies.

---

## 🧰 Step 9) Prove all communication modes explicitly (quick checklist + tests) (10 min)

Run these to be absolutely sure you’ve satisfied every requirement:

- **Host → container (API)**: `curl -s http://localhost:5012/health` ✅  
- **Host → container (Web)**: open http://localhost:8080/ ✅  
- **Container → container (Web → API)**: open web, it calls `http://api:5012/hello` (DNS) ✅  
- **Container → container (API → DB)**: `docker compose exec api curl -s http://localhost:5012/health` shows `db_ok:true` ✅  
- **Host → container file read**: edit `./shared/message.txt` on host → refresh API response shows new text ✅  
- **Container → host file write (optional)**: have API write to `/logs/api.log` → see file appear in `./shared/logs/` on host ✅  
- **Same network**: `docker network inspect docker-learning_appnet` shows all three containers attached ✅

---

## 🧭 Step 10) Next-level (optional but highly educational) to “implement everything” even deeper

- **Multi-stage builds** to shrink images (add build stage for web/api).  
- **Non-root user** in Dockerfiles for better security.  
- **Config via `.env`** + `env_file` in Compose.  
- **Add a reverse proxy (Traefik/Nginx)** container to put web+api behind one port.  
- **Add a background worker** container (Celery/RQ) that also talks to DB/API via network.  
- **Observability**: add `dozzle` or `pgadmin` as extra containers on the same network (great for learning).

---

***

## 🔀 Step 11) Create a second repo/project that talks to the existing repo over the same Docker network (30–45 min)

We’ll now move from “multiple containers in one project” to “multiple repos/projects working together”, while still keeping everything on the same user-defined Docker network.
The new repo will be a small **worker/bridge app** that can:

- call the existing `api` from another repo,
- read files from the host,
- write results back to the host,
- and prove cross-repo container communication.


### 1. Create a second repo/project folder

On the host, create a sibling project next to your existing Docker learning app:

```bash
cd .
mkdir -p ../notify_worker
cd ../notify_worker
```

Example structure:

```bash
notify_worker/
├── app.py
├── requirements.txt
├── Dockerfile
└── shared/
```


### 2. Create `app.py`

This app will:

- call the existing repo’s API using container DNS,
- read an input file from the host,
- and write an output file back to the host.

```python
from flask import Flask, jsonify
from pathlib import Path
import os, requests, datetime

app = Flask(__name__)

API_URL = os.getenv("API_URL", "http://api:5012")
INPUT_FILE = Path("/shared/instructions.txt")
OUTPUT_FILE = Path("/shared/worker-output.log")

@app.get("/health")
def health():
    return jsonify(status="ok", api_url=API_URL)

@app.get("/sync")
def sync():
    try:
        host_text = INPUT_FILE.read_text().strip() if INPUT_FILE.exists() else "no host input file found"
    except Exception as e:
        host_text = f"error reading host file: {e}"

    try:
        r = requests.get(f"{API_URL}/hello", params={"name": "worker-repo"}, timeout=5)
        r.raise_for_status()
        api_data = r.json()
    except Exception as e:
        api_data = {"error": str(e)}

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        f"time={datetime.datetime.utcnow().isoformat()}Z\n"
        f"host_text={host_text}\n"
        f"api_data={api_data}\n"
    )

    return jsonify(
        status="synced",
        host_text=host_text,
        api_data=api_data,
        wrote_to=str(OUTPUT_FILE)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
```


### 3. Create `requirements.txt`

```txt
flask==3.0.3
requests==2.32.3
```


### 4. Create `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8090
CMD ["python", "app.py"]
```


### 5. Build the second repo image

```bash
cd ~/notify_worker
docker build -t learn_docker/notify_worker:1.0 .
```


### 6. Prepare shared host files

```bash
mkdir -p ~/notify_worker/shared
echo "Message coming from host into second repo" > ~/notify_worker/shared/instructions.txt
```


### 7. Run the second repo container on the **same network** as the first repo

Use the same network name that your first project already uses (`appnet` in the earlier steps):

```bash
docker run --rm -d \
  --name notify_worker \
  --network appnet \
  -p 8090:8090 \
  -e API_URL=http://api:5012 \
  -v ~/notify_worker/shared:/shared \
  learn_docker/notify_worker:1.0
```


### 8. Test from host

```bash
curl -s http://localhost:8090/health
curl -s http://localhost:8090/sync
cat ~/notify_worker/shared/worker-output.log
```

✅ You now have a **second repo/project** with its own image and container, talking to the first repo’s `api`, reading from host files, and writing back to the host.

***

## 🌉 Step 12) Add a third repo/project that talks to both repos and proves multi-repo communication (30–45 min)

Now create one more independent repo/project so the final setup is not just “repo A calls repo B”, but “repo C communicates with services from repo A and repo B”.
This makes the learning path closer to real-world microservice setups where independent repositories share a Docker network.

### 1. Create the third repo/project

```bash
cd .
mkdir -p ../ops_console
cd ../ops_console
```


### 2. Create `app.py`

This app will:

- call the original repo’s `api`,
- call the second repo’s `notify_worker`,
- expose its own endpoint to the host,
- and read a host-mounted file too.

```python
from flask import Flask, jsonify
from pathlib import Path
import os, requests

app = Flask(__name__)

API_URL = os.getenv("API_URL", "http://api:5012")
WORKER_URL = os.getenv("WORKER_URL", "http://notify_worker:8090")
NOTES_FILE = Path("/ops/notes.txt")

@app.get("/health")
def health():
    return jsonify(status="ok")

@app.get("/status")
def status():
    try:
        api_resp = requests.get(f"{API_URL}/health", timeout=5).json()
    except Exception as e:
        api_resp = {"error": str(e)}

    try:
        worker_resp = requests.get(f"{WORKER_URL}/health", timeout=5).json()
    except Exception as e:
        worker_resp = {"error": str(e)}

    try:
        notes = NOTES_FILE.read_text().strip() if NOTES_FILE.exists() else "no ops notes found"
    except Exception as e:
        notes = f"error reading notes: {e}"

    return jsonify(
        ops="ok",
        api=api_resp,
        worker=worker_resp,
        notes=notes
    )

@app.get("/run-check")
def run_check():
    try:
        worker_sync = requests.get(f"{WORKER_URL}/sync", timeout=10).json()
    except Exception as e:
        worker_sync = {"error": str(e)}

    try:
        api_hello = requests.get(f"{API_URL}/hello", params={"name": "ops-console"}, timeout=5).json()
    except Exception as e:
        api_hello = {"error": str(e)}

    return jsonify(
        status="done",
        worker_sync=worker_sync,
        api_hello=api_hello
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8070)
```


### 3. Create `requirements.txt`

```txt
flask==3.0.3
requests==2.32.3
```


### 4. Create `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8070
CMD ["python", "app.py"]
```


### 5. Build the third repo image

```bash
cd ~/ops_console
docker build -t learn_docker/ops_console:1.0 .
```


### 6. Add host-side files for this repo too

```bash
mkdir -p ~/ops_console/shared
echo "ops console can read this from host" > ~/ops_console/shared/notes.txt
```


### 7. Run it on the same Docker network

```bash
docker run --rm -d \
  --name ops_console \
  --network appnet \
  -p 8070:8070 \
  -e API_URL=http://api:5012 \
  -e WORKER_URL=http://notify_worker:8090 \
  -v ~/ops_console/shared:/ops \
  learn_docker/ops_console:1.0
```


### 8. Test from host

```bash
curl -s http://localhost:8070/health
curl -s http://localhost:8070/status
curl -s http://localhost:8070/run-check
```

✅ You now have **three separate apps/projects** participating in the same Docker network:

- existing repo: `web`, `api`, `db`
- second repo: `notify_worker`
- third repo: `ops_console`

***

## 🧪 Step 13) Prove cross-repo inter-container and host communication explicitly (15–20 min)

Your goal here is to verify every communication direction clearly, not just assume it works.
These checks mirror the learning style already used in the existing steps, where each capability is tested from both the host and from containers on the same network.[^1_1]

### 1. Host → repo 1

```bash
curl -s http://localhost:5012/health
curl -s "http://localhost:5012/hello?name=host-check"
curl -s http://localhost:8080/
```


### 2. Host → repo 2

```bash
curl -s http://localhost:8090/health
curl -s http://localhost:8090/sync
```


### 3. Host → repo 3

```bash
curl -s http://localhost:8070/health
curl -s http://localhost:8070/status
curl -s http://localhost:8070/run-check
```


### 4. Repo 2 container → repo 1 container

Run a curl from inside the second repo container:

```bash
docker exec -it notify_worker sh
```

Inside:

```bash
apt-get update && apt-get install -y curl
curl -s http://api:5012/health
exit
```


### 5. Repo 3 container → repo 1 and repo 2 containers

```bash
docker exec -it ops_console sh
```

Inside:

```bash
apt-get update && apt-get install -y curl
curl -s http://api:5012/health
curl -s http://notify_worker:8090/health
exit
```


### 6. Host file → container read

Update files on the host:

```bash
echo "updated by host for worker repo" > ~/notify_worker/shared/instructions.txt
echo "updated by host for ops repo" > ~/ops_console/shared/notes.txt
```

Retest:

```bash
curl -s http://localhost:8090/sync
curl -s http://localhost:8070/status
```


### 7. Container → host file write

Check the file written by the second repo:

```bash
cat ~/notify_worker/shared/worker-output.log
```


### 8. Same network verification

```bash
docker network inspect appnet
```

You should see at least:

- `api`
- `web`
- `db`
- `notify_worker`
- `ops_console`

✅ This proves:

- **inter-container communication** across repos,
- **intra-container behavior** inside each app,
- **same-network communication** by container name,
- and **host ↔ container file communication**.

***

## 🧩 Step 14) Make the additional repo/project reproducible with Docker Compose too (20–30 min)

The original document already uses Compose later to make one project reproducible, so the next logical learning step is to do the same for a second independent repo and then connect both repos using one shared external network.[^1_1]
This is the cleanest real-world pattern for “different repos, different Compose files, same network”.[^1_1]

### 1. Create a shared external network once

Run this only once on the host:

```bash
docker network create shared_cross_repo_net
```


### 2. Update repo 1 Compose to use the external network

In the **existing repo**, add or replace the network section like this:

```yaml
networks:
  shared_cross_repo_net:
    external: true
```

Then update each service (`api`, `web`, `db`) to use it:

```yaml
services:
  db:
    networks: [shared_cross_repo_net]

  api:
    networks: [shared_cross_repo_net]

  web:
    networks: [shared_cross_repo_net]
```


### 3. Create `docker-compose.yml` in `~/notify_worker`

```yaml
version: "3.9"

services:
  notify_worker:
    build: .
    container_name: notify_worker
    environment:
      API_URL: http://api:5012
    ports:
      - "8090:8090"
    volumes:
      - ./shared:/shared
    networks:
      - shared_cross_repo_net

networks:
  shared_cross_repo_net:
    external: true
```


### 4. Create `docker-compose.yml` in `~/ops_console`

```yaml
version: "3.9"

services:
  ops_console:
    build: .
    container_name: ops_console
    environment:
      API_URL: http://api:5012
      WORKER_URL: http://notify_worker:8090
    ports:
      - "8070:8070"
    volumes:
      - ./shared:/ops
    networks:
      - shared_cross_repo_net

networks:
  shared_cross_repo_net:
    external: true
```


### 5. Start the repos independently

First repo:

```bash
cd .
docker compose up --build -d
```

Second repo:

```bash
cd ~/notify_worker
docker compose up --build -d
```

Third repo:

```bash
cd ~/ops_console
docker compose up --build -d
```


### 6. Verify end-to-end across repos

```bash
curl -s http://localhost:8090/sync
curl -s http://localhost:8070/status
curl -s http://localhost:8070/run-check
docker network inspect shared_cross_repo_net
```

✅ At this stage, you have completed the target outcome:

- at least **one additional repo/project is built**,
- multiple repos run as containers,
- they communicate over the **same Docker network**,
- they support **inter-container and cross-repo communication**,
- and they can **read/write host files** and expose ports to the host.

***

## 🧭 Step 15) Final checklist for the multi-repo Docker setup (10 min)

Use this as the final success checklist for the new part of the learning plan.
It extends the same verification mindset already present in the existing todo, but now at the **cross-repo** level instead of only within one app stack.[^1_1]

- ✅ Repo 1 is running its original services (`web`, `api`, `db`).
- ✅ Repo 2 (`notify_worker`) is built and reachable from the host on port `8090`.
- ✅ Repo 3 (`ops_console`) is built and reachable from the host on port `8070`.
- ✅ Repo 2 can call Repo 1’s `api` using `http://api:5012`.
- ✅ Repo 3 can call both Repo 1 and Repo 2 using container DNS names.
- ✅ Repo 2 reads host file input from `~/notify_worker/shared/instructions.txt`.
- ✅ Repo 2 writes host file output to `~/notify_worker/shared/worker-output.log`.
- ✅ Repo 3 reads host file input from `~/ops_console/shared/notes.txt`.
- ✅ All containers are attached to the same Docker network.
- ✅ The setup works both with `docker run` and with separate Compose files.

---

## 🔐 Step 16) Understand Docker users, Linux ownership, and why permissions matter (20–30 min)

Before changing permissions across containers and projects, you need to understand one critical idea:

> Containers do NOT magically bypass Linux permissions.

Every container process runs as:

* `root` (UID 0) by default, OR
* a specific Linux user inside the container.

And every mounted host file still belongs to:

* a Linux user on the host,
* with a UID/GID,
* and Linux permission rules still apply.

This means:

* a container user may NOT be able to read/write host files,
* two containers may NOT be able to share mounted files,
* two projects on the same Docker network may communicate over HTTP but still fail file access,
* and non-root containers behave very differently from root containers.

You are now going to learn all permission combinations step-by-step.

By the end of these steps, you will clearly understand:

* default container root user,
* container-specific users,
* project-specific shared users,
* host ↔ container ownership,
* inter-container permissions,
* inter-project permissions,
* cross-user communication,
* and secure alternatives to running everything as root.

---

## 👤 Step 17) Inspect the default container user (root) (15–20 min)

Docker containers run as `root` unless explicitly changed.

### 1. Start a temporary container

```bash
docker run --rm -it alpine sh
```

### 2. Check the active user

Inside the container:

```bash
whoami
id
pwd
```

You should see:

```bash
root
uid=0(root) gid=0(root)
```

### 3. Create files as root inside the container

```bash
mkdir /demo
cd /demo

echo "created by container root" > root-file.txt
ls -l
```

### 4. Exit

```bash
exit
```

This proves:

* containers run as root by default,
* root can create files anywhere inside the container filesystem,
* container root is NOT automatically your host user.

---

## 🏠 Step 18) Understand host ↔ container ownership mismatch (20–30 min)

Now you will prove why bind-mounted files often become permission problems.

### 1. Create a host directory

```bash
mkdir -p ~/docker_permission_demo/shared
```

### 2. Run a container mounting the host directory

```bash
docker run --rm -it \
  -v ~/docker_permission_demo/shared:/shared \
  alpine sh
```

### 3. Create a file from inside the container

Inside:

```bash
echo "written by container root" > /shared/root-created.txt
exit
```

### 4. Inspect from host

```bash
ls -ln ~/docker_permission_demo/shared
```

You will usually see:

```bash
-rw-r--r-- 1 0 0 ... root-created.txt
```

OR a UID like:

```bash
-rw-r--r-- 1 0 0
```

This means:

* the file is owned by container root,
* which maps to host root,
* not your normal host user.

### 5. Try editing the file from host

```bash
nano ~/docker_permission_demo/shared/root-created.txt
```

Depending on OS setup, you may:

* succeed,
* get permission denied,
* or require sudo.

✅ You have now proven the most common Docker permission issue.

---

## 🔍 Step 19) Learn UID/GID mapping between host and containers (20–30 min)

Docker permissions are based on numeric IDs, NOT usernames.

### 1. Check your host user ID

On host:

```bash
id
```

Example:

```bash
uid=1000(vijay) gid=1000(vijay)
```

### 2. Start a container with the SAME UID/GID

Replace `1000:1000` if your IDs differ.

```bash
docker run --rm -it \
  --user 1000:1000 \
  -v ~/docker_permission_demo/shared:/shared \
  alpine sh
```

### 3. Create files

Inside:

```bash
whoami
id

echo "created with matching UID" > /shared/user-owned.txt
exit
```

### 4. Verify from host

```bash
ls -ln ~/docker_permission_demo/shared
```

You should now see your host UID/GID owning the file.

✅ This is the foundation for secure host ↔ container communication.

---

## 👥 Step 20) Create a non-root user inside a custom container (30–40 min)

Now modify one of your earlier projects to use a dedicated container user.

You will NOT modify earlier steps.
This is an additional learning experiment.

### 1. Create a new learning app

```bash
mkdir -p ~/docker_users_demo/app
cd ~/docker_users_demo/app
```

### 2. Create `app.py`

```python
from flask import Flask
import os

app = Flask(__name__)

@app.get("/")
def home():
    return {
        "user": os.popen("whoami").read().strip(),
        "uid": os.popen("id -u").read().strip(),
        "gid": os.popen("id -g").read().strip()
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
```

### 3. Create `requirements.txt`

```txt
flask==3.0.3
```

### 4. Create Dockerfile with custom user

```dockerfile
FROM python:3.12-slim

RUN groupadd -g 2001 appgroup && \
    useradd -m -u 2001 -g appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 5050

CMD ["python", "app.py"]
```

### 5. Build image

```bash
docker build -t learn_docker/non_root_app:1.0 .
```

### 6. Run container

```bash
docker run --rm -p 5050:5050 learn_docker/non_root_app:1.0
```

### 7. Test from host

Open:

```bash
http://localhost:5050
```

You should see:

```json
{
  "user": "appuser",
  "uid": "2001",
  "gid": "2001"
}
```

✅ You now understand container-specific users.

---

## 📂 Step 21) Host ↔ non-root container file permissions (30–45 min)

Now you will prove why non-root containers cannot automatically write to host folders.

### 1. Create host folder

```bash
mkdir -p ~/docker_users_demo/shared
```

### 2. Give ownership ONLY to your host user

```bash
ls -ld ~/docker_users_demo/shared
```

### 3. Run the non-root container with bind mount

```bash
docker run --rm -it \
  -p 5050:5050 \
  -v ~/docker_users_demo/shared:/shared \
  learn_docker/non_root_app:1.0 sh
```

### 4. Try writing into `/shared`

Inside:

```bash
echo "hello" > /shared/test.txt
```

You will likely get:

```bash
Permission denied
```

This proves:

* non-root container users are restricted,
* bind mounts preserve host ownership,
* permissions matter even when Docker networking works.

---

## 🔧 Step 22) Fix host ↔ container permissions using shared UID/GID (30–45 min)

This is the preferred real-world solution.

### 1. Find your host UID/GID

```bash
id
```

Example:

```bash
uid=1000 gid=1000
```

### 2. Create a new Dockerfile using host-compatible IDs

```dockerfile
FROM python:3.12-slim

ARG UID=1000
ARG GID=1000

RUN groupadd -g ${GID} appgroup && \
    useradd -m -u ${UID} -g appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN chown -R appuser:appgroup /app

USER appuser

CMD ["python", "app.py"]
```

### 3. Build using your actual UID/GID

```bash
docker build \
  --build-arg UID=$(id -u) \
  --build-arg GID=$(id -g) \
  -t learn_docker/non_root_app:2.0 .
```

### 4. Run with mounted directory

```bash
docker run --rm -it \
  -v ~/docker_users_demo/shared:/shared \
  learn_docker/non_root_app:2.0 sh
```

### 5. Write file

Inside:

```bash
echo "works now" > /shared/fixed.txt
exit
```

### 6. Verify from host

```bash
ls -l ~/docker_users_demo/shared
```

You should now see your host user owning the file.

✅ You now understand secure host ↔ container file sharing.

---

## 🔄 Step 23) Inter-container permissions using shared mounted folders (30–45 min)

Networking and file permissions are separate concepts.

Two containers may:

* communicate over HTTP successfully,
* but still fail to share files.

Now you will prove it.

### 1. Create a shared host folder

```bash
mkdir -p ~/cross_container_permissions/shared
```

### 2. Start container A as UID 2001

```bash
docker run --rm -d \
  --name writer_a \
  --user 2001:2001 \
  -v ~/cross_container_permissions/shared:/shared \
  alpine sh -c "while true; do echo A >> /shared/data.txt; sleep 5; done"
```

### 3. Start container B as UID 3001

```bash
docker run --rm -it \
  --name reader_b \
  --user 3001:3001 \
  -v ~/cross_container_permissions/shared:/shared \
  alpine sh
```

### 4. Try reading and writing

Inside container B:

```bash
cat /shared/data.txt

echo "B" >> /shared/data.txt
```

Depending on ownership and permissions, writes may fail.

### 5. Inspect permissions from host

```bash
ls -ln ~/cross_container_permissions/shared
```

✅ You have now proven:

* inter-container networking is NOT file permission sharing,
* container users matter across shared volumes,
* different users create cross-container permission conflicts.

---

## 🌉 Step 24) Create a shared group for multiple containers (30–45 min)

This is a common production approach.

Instead of:

* making everything root,
* or forcing same user IDs,

multiple containers can share a Linux group.

### 1. Create shared folder

```bash
mkdir -p ~/shared_group_demo/data
```

### 2. Allow group write permissions

```bash
chmod 2775 ~/shared_group_demo/data
```

The `2` sets the SGID bit.
New files inherit the directory group.

### 3. Run container A with shared group

```bash
docker run --rm -d \
  --name group_writer \
  --user 2001:4000 \
  -v ~/shared_group_demo/data:/shared \
  alpine sh -c "echo hello-from-A > /shared/group.txt && sleep 99999"
```

### 4. Run container B with SAME group

```bash
docker run --rm -it \
  --name group_reader \
  --user 3001:4000 \
  -v ~/shared_group_demo/data:/shared \
  alpine sh
```

### 5. Test access

Inside container B:

```bash
cat /shared/group.txt

echo "from B" >> /shared/group.txt
```

This should now work.

✅ You now understand group-based permission sharing between containers.

---

## 🧱 Step 25) Inter-project permissions across different Docker Compose projects (40–60 min)

Now apply permissions to MULTIPLE projects.

You already created:

* repo 1 (`api`, `web`, `db`)
* repo 2 (`notify_worker`)
* repo 3 (`ops_console`)

Now you will make them securely share files.

### 1. Create shared cross-project folder

```bash
mkdir -p ~/cross_project_shared
```

### 2. Set permissive group ownership

```bash
sudo chgrp -R $(id -g) ~/cross_project_shared
chmod -R 2775 ~/cross_project_shared
```

### 3. Update repo 1 compose

Add shared volume:

```yaml
volumes:
  - ~/cross_project_shared:/shared
```

Run services as your host UID/GID:

```yaml
user: "1000:1000"
```

Replace with your actual IDs.

### 4. Update repo 2 compose

```yaml
services:
  notify_worker:
    user: "1000:1000"
    volumes:
      - ~/cross_project_shared:/shared
```

### 5. Update repo 3 compose

```yaml
services:
  ops_console:
    user: "1000:1000"
    volumes:
      - ~/cross_project_shared:/shared
```

### 6. Restart all projects

Repo 1:

```bash
docker compose up -d --build
```

Repo 2:

```bash
docker compose up -d --build
```

Repo 3:

```bash
docker compose up -d --build
```

### 7. Verify shared access

Inside repo 1 container:

```bash
docker exec -it api sh

echo "hello from api" > /shared/demo.txt
exit
```

Inside repo 2 container:

```bash
docker exec -it notify_worker sh

cat /shared/demo.txt

echo "reply from worker" >> /shared/demo.txt
exit
```

Inside repo 3 container:

```bash
docker exec -it ops_console sh

cat /shared/demo.txt
exit
```

✅ You now have inter-project file permissions working securely.

---

## 🚫 Step 26) Learn why running everything as root is dangerous (20–30 min)

Root containers can:

* overwrite mounted host files,
* delete shared project data,
* modify permissions unexpectedly,
* and create security risks.

### 1. Run a root container against shared data

```bash
docker run --rm -it \
  -v ~/cross_project_shared:/shared \
  alpine sh
```

### 2. Change permissions destructively

Inside:

```bash
chmod 000 /shared/demo.txt
exit
```

### 3. Try reading from another container

```bash
docker exec -it notify_worker sh
cat /shared/demo.txt
```

You may now get:

```bash
Permission denied
```

### 4. Fix from host

```bash
chmod 664 ~/cross_project_shared/demo.txt
```

✅ You now understand why production containers should avoid root when possible.

---

## 🔐 Step 27) Learn read-only vs read-write mounts across containers and projects (20–30 min)

Not every container should be allowed to modify shared files.

### 1. Mount shared folder as read-only in repo 3

```yaml
volumes:
  - ~/cross_project_shared:/shared:ro
```

### 2. Restart repo 3

```bash
docker compose up -d
```

### 3. Test permissions

Inside repo 3 container:

```bash
docker exec -it ops_console sh
```

Try:

```bash
cat /shared/demo.txt

echo "should fail" >> /shared/demo.txt
```

Write should fail.

✅ You now understand:

* read-only mounts,
* secure shared data patterns,
* and limiting cross-project write access.

---

## 🧪 Step 28) Final end-to-end permission verification matrix (20–30 min)

At this stage you should explicitly test every permission scenario.

### A. Default root container

```bash
docker run --rm alpine whoami
```

Expected:

```bash
root
```

---

### B. Container-specific user

```bash
docker run --rm --user 2001:2001 alpine id
```

Expected:

```bash
uid=2001 gid=2001
```

---

### C. Host ↔ container permissions

Container writes file.
Host edits it.
Container reads it again.

Verify ownership with:

```bash
ls -ln
```

---

### D. Inter-container communication

Container A:

```bash
curl http://container-b:PORT
```

Verify networking works independently from file permissions.

---

### E. Inter-container shared files

Container A writes.
Container B reads.
Container B appends.

Verify:

* ownership,
* groups,
* write permissions.

---

### F. Inter-project communication

Repo 1 service:

```bash
curl http://notify_worker:8090/health
```

Repo 2 service:

```bash
curl http://api:5012/health
```

Repo 3 service:

```bash
curl http://notify_worker:8090/sync
```

---

### G. Read-only mounts

Verify:

```bash
Permission denied
```

occurs correctly when expected.

---

### H. Root override testing

Verify root containers can bypass restrictions.

Then restore permissions safely.

---

## 🏁 Step 29) Final learning outcomes achieved

You have now implemented and proven:

### Users and ownership

* default Docker root user,
* container-specific users,
* host UID/GID mapping,
* project-specific shared users,
* Linux groups for shared access.

### Communication

* host ↔ container communication,
* container ↔ container communication,
* inter-project communication,
* multi-project networking.

### Permissions

* root-owned files,
* non-root restrictions,
* bind mount ownership,
* shared group access,
* read-only mounts,
* secure write permissions.

### Cross-system behavior

* inter-container file sharing,
* inter-project file sharing,
* different-user communication,
* secure multi-container collaboration.

At this point you now understand one of the most important real-world Docker topics:


