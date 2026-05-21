# 09 — Commands: Everything You Need to Run the System

> Every command you will ever need, explained with what it does and when to use it.

---

## First Time Setup

> **Note:** the recommended way to run this app is via Docker Compose — it brings up the Streamlit app, the PostgreSQL database, and the background scheduler together. The "local venv" instructions below are kept for development convenience.

### Quickstart with Docker (recommended)

```bash
docker compose up -d --build         # build images + start everything
docker compose logs -f app           # follow app startup logs

# First time only: create your admin account
docker exec -it ops-copilot-app python -c \
  'from auth.auth import create_user; create_user("admin", "ChangeMe123!", "Administrator", role="admin")'
```

Then open https://localhost:8501 and log in. To stop: `docker compose down`. To stop *and wipe user data*: `docker compose down -v` (this deletes the postgres volume — be careful).

### 1. Clone and enter the project

```bash
cd ops-copilot
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

**What this does:** Creates a folder called `venv/` containing an isolated Python installation. This keeps this project's dependencies separate from other Python projects on your machine. Think of it as a "clean room" for this project.

### 3. Activate the virtual environment

```bash
# On Linux / macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

**What this does:** Your terminal prompt will show `(venv)` at the start. Now when you run `python` or `pip`, it uses the isolated environment, not your system Python.

**You must run this every time you open a new terminal window before running the app.**

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

**What this does:** Downloads and installs all Python libraries listed in `requirements.txt`. This takes a few minutes the first time. Major ones:

| Package | Purpose |
|---------|---------|
| `streamlit` | Web framework |
| `google-genai` | Gemini API client |
| `chromadb` | Vector database |
| `sentence-transformers` | Embedding model |
| `bcrypt` | Password hashing |
| `langchain` | Document loading utilities |
| `ragas` | AI evaluation framework |

### 5. Set up your API key and session secret

```bash
# The .env file is already there — just verify it has your keys:
cat .env
```

It should contain at minimum:
```
GOOGLE_API_KEY=AIzaSy...your key here...
DATABASE_URL=postgresql://ops_user:ops_password@postgres:5432/ops_copilot
SESSION_SECRET=<64 hex characters — used to sign persistent-login URL tokens>
```

If `GOOGLE_API_KEY` is wrong, Gemini calls fail with an auth error. If `SESSION_SECRET` is missing, the app generates an ephemeral one at startup and prints a warning — users will be logged out on every container restart. Generate one once with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Then paste it into `.env` as `SESSION_SECRET=...`.

---

## Ingest Documents (Run Before First Use)

### Ingest all documents

```bash
python ingest.py
```

**What this does:**
1. Reads all files from `data/markdown/`, `data/pdf/`, `data/yaml/`
2. Splits them into chunks of 1000 characters
3. Converts each chunk to a 768-number vector (embedding) using BGE base
4. Stores everything in `chroma_db/`
5. Saves a hash of each file to `ingestion_state.json`

**When to run:** Before the first use, and whenever you add new documents.

**Time:** ~30-60 seconds for a small document set.

### Clear the database and re-ingest from scratch

```bash
python ingest.py --clear
```

**What this does:** Deletes all chunks from ChromaDB first, then runs the normal ingestion pipeline.

**When to run:** When you've modified existing documents (not just added new ones). Without `--clear`, the old chunks from the modified file would remain alongside the new ones.

### Check how many chunks are in the database

```python
# Quick Python check:
python3 -c "
import chromadb
c = chromadb.PersistentClient('./chroma_db')
col = c.get_collection('ops_knowledge')
print(f'Chunks in database: {col.count()}')
"
```

---

## Run the App

### Start with HTTPS (recommended)

```bash
streamlit run app.py \
  --server.sslCertFile=certs/cert.pem \
  --server.sslKeyFile=certs/key.pem \
  --server.port=8501
```

**What this does:** Starts the Streamlit server on port 8501 with TLS encryption. The app is accessible at `https://localhost:8501`.

**Why HTTPS:** Encrypts all traffic including passwords and queries. Without HTTPS, a network sniffer could capture credentials.

### Start without HTTPS (development only)

```bash
streamlit run app.py
```

Access at `http://localhost:8501`. Use only for local development where security doesn't matter.

### Start on a different port

```bash
streamlit run app.py --server.port=8502
```

Useful if port 8501 is already in use.

### Run in background (Linux server)

```bash
nohup streamlit run app.py \
  --server.sslCertFile=certs/cert.pem \
  --server.sslKeyFile=certs/key.pem \
  --server.port=8501 \
  --server.headless=true > streamlit.log 2>&1 &
```

**What this does:**
- `nohup` — keeps the process running even if you close the terminal
- `--server.headless=true` — doesn't try to open a browser (needed on servers)
- `> streamlit.log 2>&1` — saves all output to `streamlit.log`
- `&` — runs in the background

### Stop the background process

```bash
# Find the process:
ps aux | grep streamlit

# Kill it:
kill <PID>
```

---

## Evaluate RAG Quality

### Run evaluation

```bash
python evaluate.py
```

**What this does:** Runs 5 test questions through the RAG system, computes RAGAS faithfulness and answer relevancy scores, saves results to `evaluation_results.json`.

**Time:** 2-5 minutes (multiple Gemini API calls).

**When to run:**
- After ingesting new documents
- After changing config settings (chunk size, TOP_K)
- Weekly to track quality over time

---

## User Management (Command Line)

These are alternative to using the Admin Panel web UI.

### Add a new user

```bash
docker exec -it ops-copilot-app python3 -c '
from auth.auth import create_user
success = create_user(
    username="newuser",
    password="SecurePass123!",
    display_name="New User (SRE)",
    role="sre",
)
print("Created:", success)
'
```

Note the single quotes around the python `-c` block — required when your password contains `!`, which bash interprets as history expansion inside double quotes.

### Hash a password manually

```bash
docker exec -it ops-copilot-app python3 -c '
from auth.auth import hash_password
print(hash_password("MyPassword123"))
'
```

### Verify a password against a stored hash

```bash
docker exec -it ops-copilot-app python3 -c '
from auth.auth import verify_password
print("Match:", verify_password("MyPassword123", "$2b$12$..."))
'
```

---

## Testing

### Run all tests

```bash
python -m pytest tests/ -v
```

### Run a single test file

```bash
python -m pytest tests/test_auth.py -v
```

### Quick RAG test (from command line)

```bash
python core/rag.py
```

This runs `test_rag()` at the bottom of core/rag.py, which asks a hardcoded test question and prints the answer.

---

## Checking Logs

All logs now live in PostgreSQL — use `psql` inside the container, or the helper functions in Python.

### Open a psql shell

```bash
docker exec -it ops-copilot-postgres psql -U ops_user -d ops_copilot
```

Inside psql: `\dt` lists tables, `\q` quits.

### View recent queries

```bash
docker exec -it ops-copilot-postgres psql -U ops_user -d ops_copilot -c \
  "SELECT timestamp, username, LEFT(question, 50) FROM query_log ORDER BY timestamp DESC LIMIT 5;"
```

### View recent security events

```bash
docker exec -it ops-copilot-postgres psql -U ops_user -d ops_copilot -c \
  "SELECT timestamp, event_type, username FROM audit_log ORDER BY timestamp DESC LIMIT 10;"
```

### Check for failed login attempts (via Python helper)

```bash
docker exec -it ops-copilot-app python3 -c "
from monitoring.audit_log import get_failed_logins_last_n_minutes
failures = get_failed_logins_last_n_minutes(60)
print(f'Failed logins in last 60 min: {len(failures)}')
for f in failures:
    print(f['timestamp'], f['username'], f['details'])
"
```

---

## Docker (Standard Workflow)

```bash
# Build + start everything (app + postgres + scheduler)
docker compose up -d --build

# View live logs for one service
docker compose logs -f app

# Re-ingest documents inside the app container
docker exec -it ops-copilot-app python ingest.py

# Re-ingest from scratch (wipes ChromaDB first)
rm -rf chroma_db/* && docker exec -it ops-copilot-app python ingest.py

# Stop everything (data preserved)
docker compose down

# Stop and DELETE the postgres volume (also wipes all users, audit log, query log)
docker compose down -v
```

Tip: if you change Python code, run `docker compose up -d --build` to bake the changes into the image. Files under `data/`, `chroma_db/` and the JSON state file are bind-mounted, so edits to those don't need a rebuild.

---

## Summary: Most Common Commands

| Situation | Command |
|-----------|---------|
| First time setup | `docker compose up -d --build` |
| Create first admin user | `docker exec -it ops-copilot-app python -c 'from auth.auth import create_user; create_user("admin", "Pass123!", "Admin", role="admin")'` |
| Added new documents | `docker exec -it ops-copilot-app python ingest.py` |
| Modified existing docs | `rm -rf chroma_db/* && docker exec -it ops-copilot-app python ingest.py` |
| Restart after code change | `docker compose up -d --build` |
| Check AI quality | `docker exec -it ops-copilot-app python evaluate.py` |
| Add a new team member | Use Admin Panel at `/Admin_Panel` |
| Check for attacks | Query the `audit_log` table or use Admin Panel |
| Check usage stats | Open Usage Dashboard in the app |
