# Azure VM Deployment Plan

This document explains:
1. What our current Docker Compose system looks like
2. What we need to change before running it on an Azure VM
3. Which components are fine as-is, and which need upgrading

Written in simple language. No deep cloud knowledge needed.

---

## 1. Our Target Scale

| Metric | Value |
|---|---|
| Total users | 50 - 60 internal WSO2 engineers |
| Concurrent users (peak) | 40 - 50 |
| Deployment target | One Azure Virtual Machine |
| Access | Internal only (not public internet) |
| Run command | `docker compose up -d` |

Important: this is a **small internal tool**, not a public SaaS product. That means we do NOT need things like load balancers, Kubernetes, auto-scaling, or distributed databases. One VM is enough.

---

## 2. What We Have Today (Current Architecture)

Our `docker-compose.yml` defines **3 containers** that run together:

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure VM (one machine)                   │
│                                                             │
│  ┌───────────────┐    ┌───────────────┐   ┌─────────────┐   │
│  │   app         │    │  scheduler    │   │  postgres   │   │
│  │  (Streamlit)  │    │ (APScheduler) │   │ (database)  │   │
│  │  port 8501    │    │ every 30 min  │   │ port 5432   │   │
│  └───────┬───────┘    └───────┬───────┘   └──────┬──────┘   │
│          │                    │                  │          │
│          └────────────┬───────┴──────────────────┘          │
│                       │                                     │
│       ┌───────────────┴───────────────┐                     │
│       │       Shared volumes          │                     │
│       │  /data        (source docs)   │                     │
│       │  /chroma_db   (vector DB)     │                     │
│       │  postgres_data (user/audit)   │                     │
│       └───────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### What each container does

| Container | Purpose |
|---|---|
| `app` | The Streamlit chat UI on port 8501. Users connect to this. |
| `scheduler` | Re-ingests new documents every 30 minutes in the background. |
| `postgres` | Stores users, audit log, and query log (replaced the old JSON files). |

### What each volume stores

| Volume | What it holds | Can we lose it? |
|---|---|---|
| `./data` | Source markdown / PDF / Confluence docs | No - re-download takes time |
| `./chroma_db` | Vector embeddings of those docs | No - but can be rebuilt by running ingestion |
| `postgres_data` | Users, audit log, query log | **No - this is irreplaceable** |
| `./ingestion_state.json` | Which files we already ingested | Re-buildable |

---

## 3. Will Our Current Setup Handle 40-50 Concurrent Users?

**Short answer: yes, with the right VM size and a few changes.**

### Why ChromaDB embedded mode is OK for us

Even though ChromaDB runs as files on disk inside the `app` container, that is fine because:
- We run only **ONE** copy of the `app` container (no replicas).
- Only the `app` container reads from `/chroma_db` during queries.
- Only the `scheduler` writes to `/chroma_db`, and only every 30 minutes.
- Read/write conflict risk is very low at our scale.

So we **do NOT need** to switch to Pinecone, Azure AI Search, or pgvector. The existing ChromaDB setup is good enough.

### Why our embedding setup is OK

`BAAI/bge-base-en-v1.5` (768-dim) and the `BAAI/bge-reranker-base` cross-encoder both run locally inside the `app` container — no API calls. For 40-50 internal users searching English WSO2 docs, the two-stage retrieve-then-rerank pipeline is the right choice. We only need to revisit if:
- Docs contain non-English content (consider a multilingual BGE variant), or
- The CPU cost of the reranker becomes a bottleneck at concurrent-user peaks (drop to `RERANK_ENABLED = False` in `core/config.py`, accepting some accuracy loss).

---

## 4. What MUST Change Before Going to Azure

These are the changes that are not optional. If we skip any of them, we have a security or reliability problem.

### 4.1 Move secrets out of `docker-compose.yml`

**Problem today:** `POSTGRES_PASSWORD: ops_password` is written directly in the file. Anyone with repo access sees the production password.

**Fix:** Read from a `.env` file (already used for `app`) or from Azure Key Vault.

```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # value comes from .env
```

### 4.2 Stop exposing PostgreSQL to the network

**Problem today:**
```yaml
postgres:
  ports:
    - '5432:5432'    # makes Postgres reachable from outside the VM
```

**Fix:** Remove the `ports:` block. The `app` and `scheduler` containers can still reach Postgres internally over the Docker network. Nothing outside the VM should be able to talk to the database.

### 4.3 Add HTTPS / TLS

**Problem today:** Streamlit serves plain HTTP on port 8501. Passwords travel unencrypted.

**Fix:** Add a 4th container — a reverse proxy (Caddy is easiest, NGINX is most popular). It terminates HTTPS and forwards to Streamlit.

```yaml
caddy:
  image: caddy:2-alpine
  ports:
    - '443:443'
    - '80:80'
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile
    - caddy_data:/data
```

Then a tiny `Caddyfile`:
```
ops-copilot.wso2.internal {
    reverse_proxy app:8501
}
```

Caddy gets a free TLS certificate automatically.

### 4.4 Use persistent Azure managed disks for volumes

**Problem today:** `./data` and `./chroma_db` are bind-mounted to the host filesystem. On an Azure VM, the host filesystem on the **OS disk** can be lost if the VM is recreated.

**Fix:** Attach an **Azure Managed Disk** (e.g. 128 GB Premium SSD) to the VM, mount it at `/mnt/opscopilot`, and put all data folders there:

```
/mnt/opscopilot/data/       <- bind to /app/data
/mnt/opscopilot/chroma_db/  <- bind to /app/chroma_db
```

This way, if we resize or rebuild the VM, the disk (with our data) survives.

### 4.5 Add resource limits per container

**Problem today:** No memory or CPU limits. A runaway query could eat all VM RAM.

**Fix:** Add `deploy.resources.limits` to each service:

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

### 4.6 Set up automatic Postgres backups

**Problem today:** No backups. If Postgres data is lost, all users, audit log, and query history are gone.

**Fix:** A simple nightly `pg_dump` cron job on the VM that copies the dump to **Azure Blob Storage**.

```bash
# /etc/cron.daily/postgres-backup
docker exec ops-copilot-postgres pg_dump -U ops_user ops_copilot \
  | gzip > /backup/db-$(date +%F).sql.gz
az storage blob upload --container backups --file /backup/db-$(date +%F).sql.gz
```

---

## 5. What We Should Consider Upgrading (Optional, Recommended)

These are NOT critical, but they make the system more reliable for an internal team.

### 5.1 Move PostgreSQL to Azure Database for PostgreSQL (Flexible Server)

Right now Postgres runs in a container on the same VM. That works, but:
- Managed Azure Postgres gives us **automatic backups**, **point-in-time restore**, **patching**, and **HA option** — all without us managing it.
- It removes the "if the VM dies, the database dies with it" risk.

**Recommendation:** Worth doing. Cheap tier (`Burstable B1ms`) costs about $15-25/month and removes a lot of operational risk. We just change the connection string in `db.py`.

If we are budget-conscious or want to keep things simple, **keep Postgres in the container** and rely on nightly backups (Section 4.6).

### 5.2 Replace local username/password with WSO2 Entra ID (SSO)

Today users log in with a username/password stored in our Postgres table. For an internal tool, it is more natural to:
- Let engineers log in with their existing WSO2 corporate account
- Stop managing passwords ourselves
- Get user offboarding for free (when someone leaves, their Entra account is disabled → they lose access)

**Recommendation:** Do this in a second phase, after the basic deployment works.

### 5.3 Monitoring

For 50 users we do not need Datadog or anything heavy. Two simple things are enough:
- **Azure Monitor agent** on the VM — gives CPU / disk / memory alerts
- **Container healthchecks** (already in our compose file) — Docker will auto-restart broken containers

If we want to look at logs in one place, send container logs to **Azure Log Analytics** using the Docker logging driver.

---

## 6. Components: Keep vs Upgrade Summary

| Component | Current | Decision | Reason |
|---|---|---|---|
| Streamlit app | One container | **Keep as-is** | One instance handles 40-50 concurrent fine |
| ChromaDB | Embedded mode, files in volume | **Keep as-is** | Small scale, one writer, one reader |
| Embedding + reranker | `BAAI/bge-base-en-v1.5` + `BAAI/bge-reranker-base` (local) | **Keep as-is** | Free, runs locally, strong English retrieval quality |
| LLM | Gemini Flash | **Keep as-is** | Cheap, fast, accurate enough |
| Postgres | Container on same VM | **Optional upgrade** to Azure Postgres Flexible Server | Better backups, less ops work |
| Scheduler | APScheduler in container | **Keep as-is** | Simple and works |
| Authentication | bcrypt + Postgres users table | **Optional upgrade** to Entra ID SSO | Phase 2 - removes password management |
| HTTPS / TLS | Not configured | **Must add** (Caddy reverse proxy) | Required for production |
| Secrets | In `docker-compose.yml` | **Must move** to `.env` or Key Vault | Security |
| Postgres port exposure | Public | **Must remove** | Security |
| Backups | None | **Must add** (nightly `pg_dump` to Blob) | Data protection |
| Persistent storage | Bind mount to OS disk | **Must move** to Azure Managed Disk | Survives VM rebuild |
| Resource limits | None | **Must add** in compose file | Prevent runaway containers |

---

## 7. Recommended Azure VM Size

For 40-50 concurrent users with our workload (embeddings on CPU, Gemini calls go out to API):

| Tier | VM size | vCPU | RAM | Disk | Approx cost/month |
|---|---|---|---|---|---|
| **Starter** | `Standard_D2s_v5` | 2 | 8 GB | 64 GB Premium SSD | ~$70 |
| **Recommended** | `Standard_D4s_v5` | 4 | 16 GB | 128 GB Premium SSD | ~$140 |
| **Comfortable** | `Standard_D8s_v5` | 8 | 32 GB | 256 GB Premium SSD | ~$280 |

**Pick `D4s_v5`.** It gives plenty of headroom for embedding inference, multiple Streamlit users, the scheduler, and Postgres all on one VM.

---

## 8. Deployment Steps (High Level)

1. **Create Azure VM** — `Standard_D4s_v5`, Ubuntu 22.04, in our internal VNet (no public IP, or restrict via NSG to corporate IP range).
2. **Attach a managed disk** of 128 GB, format and mount at `/mnt/opscopilot`.
3. **Install Docker and docker-compose** on the VM (`apt install docker.io docker-compose-plugin`).
4. **Clone the repo** to `/opt/ops-copilot`.
5. **Create `.env` file** with real secrets (Postgres password, `GOOGLE_API_KEY`, etc.) — do NOT commit it.
6. **Update `docker-compose.yml`** with the changes from Section 4 (remove Postgres port, add Caddy, add resource limits, fix volume paths to `/mnt/opscopilot/...`).
7. **Run `docker compose up -d`**.
8. **Set up nightly backup cron** (Section 4.6).
9. **Configure DNS** — point `ops-copilot.wso2.internal` to the VM.
10. **Test login + a sample query** end-to-end.

That is the entire deployment. No Kubernetes, no service mesh, no autoscaling. Boring is good for an internal tool of this size.

---

## 9. What This Plan Deliberately Skips

We are **not** doing these things, and that is on purpose:

- ❌ Kubernetes / AKS — too much operational overhead for 50 users
- ❌ Pinecone / Azure AI Search — ChromaDB is sufficient
- ❌ Multiple Streamlit replicas + load balancer — one container handles our load
- ❌ Redis cache — not needed at this scale
- ❌ CDN / Front Door — internal-only tool
- ❌ Multi-region HA — internal tool, single-region is fine

If usage grows past ~200 concurrent users or we open to external customers, revisit these decisions.
