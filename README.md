# Docker Compose Learning Lab

This project is a small Docker Compose lab designed to teach four practical ideas: container-to-container communication, multiple services using the same database, multi-container orchestration with Compose, and service scaling.[1][2]

## What this setup contains

The stack contains four services:[2][3]

| Service | Purpose | Why it exists |
|---|---|---|
| `gateway` | Public entry point on port `8000` | Calls another container and also queries the database.[1] |
| `orders` | Internal API on port `8001` | Gives a second app for service-to-service communication on the Compose network.[1] |
| `postgres` | Shared PostgreSQL database | Shows how multiple containers can safely use one database at the same time.[3] |
| `adminer` | Web UI on port `8080` | Helps inspect the database without installing extra host tools. |

Compose creates a default application network and registers services in internal DNS, so `gateway` can reach `orders` by the service name `orders` instead of hardcoded container IPs.[1]

## Why these choices were made

A user-defined Compose network was chosen because service-name discovery is the normal and reliable way for containers in the same Compose project to talk to each other.[1]

PostgreSQL was chosen as the shared database because it makes it easy to demonstrate two containers reading the same data and one container writing audit entries that the other can observe. A named volume was chosen for the database because Docker-managed volumes are the normal persistence mechanism for container data, while bind mounts are better when the goal is editing host files during development.[4][2]

The Python services use bind mounts so the source code on the host is visible immediately inside the containers. That is useful in development because changes are easy to inspect and iterate on, but it is not the best pattern for production data storage.[4]

`depends_on` plus a database healthcheck were added to reduce startup race conditions, but service readiness should still be validated by the application because dependency order alone does not guarantee that a service is fully ready for traffic.[3][5]

## Project layout

```text
.
├── docker-compose.yml
├── gateway/
│   └── app.py
├── orders/
│   └── app.py
└── db-init/
    └── 001-init.sql
```

## Start the lab

1. Open a terminal in this folder.
2. Run `docker compose up --build`.
3. Wait until `postgres` becomes healthy and the two Python apps start.
4. Open these URLs:
   - `http://localhost:8000/health`
   - `http://localhost:8000/call-orders`
   - `http://localhost:8000/db-check`
   - `http://localhost:8000/write-audit`
   - `http://localhost:8080`

## What to observe

### 1. Container-to-container communication

`gateway` calls `orders` using `http://orders:8001`, which works because both services join the same Compose network and Docker provides service discovery by name.[1]

### 2. Two containers using one database

Both `gateway` and `orders` use the same `DATABASE_URL`, pointing to `postgres:5432`. This shows that multiple services can share one database as long as each service uses proper connection handling and the database itself manages concurrency.[3][1]

### 3. Compose orchestration

Compose manages services, networks, environment variables, startup dependency declarations, published ports, and persistent volumes from one file.[2][3]

### 4. Scaling

Use this command to scale the `orders` service:

```bash
docker compose up -d --scale orders=3
```

Compose supports scaling services with the `--scale` flag. When scaling, avoid fixed `container_name` values on services you want to run with multiple replicas because each replica needs a unique container identity.[6][7]

In this lab, scale `orders`, not `gateway`, because `gateway` publishes a fixed host port and `orders` is an internal service. Internal services are usually the easiest first target for scaling experiments.[1][7]

## Bind mounts vs named volumes

| Need | Use | Why |
|---|---|---|
| Edit app code live from the host | Bind mount | The host directory is mounted directly into the container, so file changes are immediately visible.[4] |
| Persist database data | Named volume | Docker manages the storage location, which is cleaner and safer for service data.[4][2] |
| Share production app state between services | Usually a database, queue, or object store | Shared files often create coordination problems unless file sharing is the real requirement. |

## Common commands

```bash
docker compose ps
docker compose logs -f gateway
docker compose logs -f orders
docker compose exec postgres psql -U app -d appdb
docker compose down
docker compose down -v
```

`docker compose down -v` deletes the named volume too, so it resets the database state. Use it only when you want a clean restart.[2][4]

## Important notes

Do not use container IP addresses for app-to-app communication in Compose. Container IPs can change, but service names stay stable within the project network.[1]

Do not store persistent database data in bind-mounted random host folders unless you intentionally need that behavior for a local experiment. Docker volumes are the cleaner default for database storage.[4]

Do not treat `depends_on` as a full readiness guarantee. A service may start but still not be ready to accept useful work, which is why healthchecks and retry logic matter.[3][5]# Learn Docker
