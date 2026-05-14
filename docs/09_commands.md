# 09 — Commands: Everything You Need to Run the System

> Every command you will ever need, explained with what it does and when to use it.

---

## First Time Setup

### 1. Clone and enter the project

```bash
cd ops-copilot_gemini
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

### 5. Set up your API key

```bash
# The .env file is already there — just verify it has your key:
cat .env
```

It should contain:
```
GOOGLE_API_KEY=AIzaSy...your key here...
```

If the key is wrong, Gemini calls will fail with an authentication error.

---

## Ingest Documents (Run Before First Use)

### Ingest all documents

```bash
python ingest.py
```

**What this does:**
1. Reads all files from `data/markdown/`, `data/pdf/`, `data/yaml/`
2. Splits them into chunks of 1000 characters
3. Converts each chunk to a 384-number vector (embedding)
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

### Add a new user (hash a new password)

```python
python3 -c "
from auth import create_user
success = create_user(
    username='newuser',
    password='SecurePass123!',
    display_name='New User (SRE)',
    role='sre'
)
print('Created:', success)
"
```

### Hash a password manually

```python
python3 -c "
from auth import hash_password
h = hash_password('MyPassword123')
print(h)
"
```

### Verify a password against a stored hash

```python
python3 -c "
from auth import verify_password
result = verify_password('MyPassword123', '\$2b\$12\$...')
print('Match:', result)
"
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
python rag.py
```

This runs `test_rag()` at the bottom of rag.py, which asks a hardcoded test question and prints the answer.

---

## Checking Logs

### View recent queries

```bash
python3 -c "
import json
with open('query_log.json') as f:
    log = json.load(f)
for q in log['queries'][-5:]:  # last 5 queries
    print(q['timestamp'], q['username'], q['question'][:50])
"
```

### View recent security events

```bash
python3 -c "
import json
with open('audit_log.json') as f:
    log = json.load(f)
for e in log['events'][-10:]:  # last 10 events
    print(e['timestamp'], e['event_type'], e['username'])
"
```

### Check for failed login attempts

```bash
python3 -c "
from audit_log import get_failed_logins_last_n_minutes
failures = get_failed_logins_last_n_minutes(60)
print(f'Failed logins in last 60 min: {len(failures)}')
for f in failures:
    print(f['timestamp'], f['username'], f['details'])
"
```

---

## Docker (Optional)

If a `Dockerfile` and `docker-compose.yml` are configured:

```bash
# Build the image
docker build -t sre-ops-copilot .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Summary: Most Common Commands

| Situation | Command |
|-----------|---------|
| First time setup | `source venv/bin/activate && pip install -r requirements.txt` |
| Added new documents | `python ingest.py` |
| Modified existing docs | `python ingest.py --clear` |
| Start the app (with HTTPS) | `streamlit run app.py --server.sslCertFile=certs/cert.pem --server.sslKeyFile=certs/key.pem` |
| Check AI quality | `python evaluate.py` |
| Add a new team member | Use Admin Panel at `/Admin_Panel` |
| Check for attacks | Read `audit_log.json` or use Admin Panel |
| Check usage stats | Open Usage Dashboard in the app |
