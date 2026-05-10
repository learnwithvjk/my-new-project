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

Do not treat `depends_on` as a full readiness guarantee. A service may start but still not be ready to accept useful work, which is why healthchecks and retry logic matter.[3][5]he stack down and back up without `-v`, then confirm database data still exists.
5. Bring the stack down with `-v`, then start again and confirm the DB resets.

### What you learn
Bind mounts are useful when host files must be edited directly, while named volumes are better for managed persistent data like a database.[4]

### Errors you may see
- Permission issues on bind-mounted files, especially on Linux hosts.
- Confusion about why DB data persists after `docker compose down`.

### How to fix
- Check file ownership and permissions for host-mounted paths.
- Remember that `docker compose down` removes containers and networks, but not named volumes unless `-v` is added.[2][4]

### Right fix
Use bind mounts for source code in development and named volumes for stateful service data. Do not put database files in your source-code bind mount.[4]

## Task 6: Learn scaling

### Goal
Scale one internal service and understand the limitations.

### Steps
1. Remove `container_name: lab-orders` from the `orders` service first.
2. Run `docker compose up -d --scale orders=3`.
3. Check the containers with `docker compose ps`.
4. Keep calling `http://localhost:8000/call-orders`.

### What you learn
Compose can start multiple replicas of a service with `--scale`, but replicated services should not have a fixed `container_name`. Fixed host port mappings can also block scaling for services exposed directly to the host.[6][7]

### Errors you may see
- Scale failure because the service has a fixed `container_name`.
- Port collision if a scaled service publishes the same host port for every replica.

### How to fix
- Remove `container_name` for services meant to scale.
- Prefer scaling internal services that do not publish fixed host ports.

### Right fix
Scale stateless internal services first. Keep the load entry point stable and let internal services fan out behind it.[7]

## Task 7: Add one more app that shares the database

### Goal
Extend the stack yourself.

### Steps
1. Copy the `orders` service block and create a new `reports` service.
2. Reuse the same `DATABASE_URL`.
3. Mount a new local folder such as `./reports:/app`.
4. Write a small app that returns order counts by status.

### What you learn
Compose makes it easy to add more services that join the same network and reuse shared infrastructure like a database.[2][1]

### Errors you may see
- Wrong path in the bind mount, so the container starts without the expected app file.
- Service starts but is unreachable because you forgot either `expose` or the correct internal port.

### How to fix
- Verify the mount path exists on the host.
- Verify the service command and listening port match the code.

### Right fix
Keep each service small, explicit, and connected through service names and shared infrastructure declarations in Compose.[2]

## Task 8: Learn the difference between startup and readiness

### Goal
Understand why `depends_on` is not enough by itself.

### Steps
1. Remove the Postgres healthcheck condition temporarily.
2. Recreate the stack several times.
3. Observe whether app containers sometimes fail early while Postgres is still starting.

### Why the error occurs
Dependency order can control when containers are started, but it does not always guarantee the dependency is ready to handle real requests. That is why healthchecks and retry logic matter.[3][5]

### Ways to fix
- Add a proper healthcheck and wait condition.
- Add application retries for database connection attempts.

### Right fix
Use both container healthchecks and application-level retry logic. That gives a more reliable system than relying on startup order alone.[3][5]

## Task 9: Clean reset and repeat

### Goal
Learn the difference between container reset and environment reset.

### Steps
1. Run `docker compose down`.
2. Start again and check whether data still exists.
3. Run `docker compose down -v`.
4. Start again and compare the database state.

### What you learn
Containers are disposable, but named volumes survive normal teardown. That distinction matters when debugging whether a problem is in the image, runtime, or stored state.[2][4]

### Right fix
Use normal `down` when debugging app containers and `down -v` only when you intentionally want to wipe persisted state.[2][4]