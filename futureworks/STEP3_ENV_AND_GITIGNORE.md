# STEP 3 — Environment Variables, .gitignore, and config.py Hardening

## Why This Matters

Your `.env` file contains your `GOOGLE_API_KEY`. If this file is accidentally pushed to Git
(a very common mistake), the key is exposed publicly and permanently — even if you delete it
later, Git history retains it. Anyone finding it can use your API quota, resulting in a large
unexpected billing or service disruption.

Additionally, `users.json` is a sensitive file containing password hashes. It should never
be in version control.

This step:
1. Hardens `.gitignore` to prevent accidental commits of sensitive files
2. Updates `config.py` to validate that the API key is present and correctly formatted
3. Creates a `.env.example` template file (safe to commit — no real secrets)
4. Sets correct file permissions for `.env`

---

## Files You Need to Change

| File | Change |
|------|--------|
| `.gitignore` | Add all sensitive file patterns |
| `config.py` | Add startup validation and clearer error messages |
| *(new)* `.env.example` | Template file safe to commit to Git |
| `.env` | Fix permissions (600 — owner read/write only) |

---

## Step 3.1 — Update .gitignore

**File: `.gitignore`** (full content — replace entire file)

```gitignore
# ── Python Runtime ────────────────────────────────────────
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.egg-info/
*.egg
.eggs/
dist/
build/
.pytest_cache/

# ── Virtual Environment ───────────────────────────────────
venv/
env/
.venv/
.env_dir/

# ── SECURITY: Never commit these ─────────────────────────
# Environment files (contain API keys)
.env
.env.local
.env.production
.env.staging
.env.development
.env.*.local

# SSL/TLS certificates and private keys
*.pem
*.key
*.crt
*.p12
*.pfx
certs/

# User credentials (contains password hashes)
users.json
users.json.backup.*
users.json.sha256.backup.*

# Migration scripts (contain plain-text passwords during setup)
migrate_passwords.py

# Setup scripts that may contain secrets
setup_env.sh

# ── Application Data (regenerated, not versioned) ─────────
query_log.json
evaluation_results.json
ingestion_state.json
audit_log.json

# ── Vector Database (large binary data, regenerated from docs) ──
chroma_db/

# ── Streamlit Session Data ────────────────────────────────
.sessions/
.streamlit/secrets.toml

# ── IDE and Editor Files ──────────────────────────────────
.vscode/
.idea/
*.swp
*.swo
*.swn
*~

# ── Operating System Files ────────────────────────────────
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# ── Test Artifacts ────────────────────────────────────────
test_output*.txt
scratch/

# ── Backup Files ──────────────────────────────────────────
*.backup
*.bak
*.old
```

**Why are some of these additions important?**

- `users.json` — contains bcrypt hashes; if committed, an attacker offline can brute-force them
- `*.pem` / `*.key` — SSL private keys; if committed, HTTPS is completely broken
- `audit_log.json` — contains user activity data; PII in some jurisdictions
- `certs/` — the entire SSL certs directory
- `migrate_passwords.py` — TEMPORARILY contains plain-text passwords during the Step 1 migration;
  you delete it after use, but gitignore adds a safety net

**Check if .env is already tracked by Git:**
```bash
# If this shows nothing, .env is not tracked (good)
git ls-files .env

# If it shows ".env", you need to remove it from tracking:
git rm --cached .env
git commit -m "Remove .env from version control - security fix"
```

**Check if users.json is tracked:**
```bash
git ls-files users.json

# If it shows "users.json", remove it:
git rm --cached users.json
git commit -m "Remove users.json from version control - security fix"
```

---

## Step 3.2 — Create .env.example (Safe Template)

This file is SAFE to commit. It contains no real secrets — just placeholder values that show
other developers what environment variables the application expects.

**File: `.env.example`** (new file — create from scratch)

```bash
# .env.example
# ── SRE Ops Copilot — Environment Variables Template ──────
# Copy this file to .env and fill in real values.
# NEVER commit .env to Git. Only commit .env.example.
#
# Usage:
#   cp .env.example .env
#   nano .env   ← fill in real values
#   source .env ← (optional, for non-Docker use)

# ── Required: Google Gemini API ───────────────────────────
# Get from: https://aistudio.google.com/app/apikey
# Starts with "AIza"
GOOGLE_API_KEY=your_google_api_key_here

# ── LLM Model ─────────────────────────────────────────────
# Options: gemini-flash-latest, gemini-1.5-pro, gemini-1.5-flash-latest
LLM_MODEL=gemini-flash-latest

# ── Embedding Model ───────────────────────────────────────
# Local model, no API key required. Downloaded automatically on first run.
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ── ChromaDB Vector Database ──────────────────────────────
CHROMA_PATH=./chroma_db
COLLECTION_NAME=ops_knowledge

# ── Document Chunking ─────────────────────────────────────
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5

# ── Data Directories ──────────────────────────────────────
MARKDOWN_DIR=./data/markdown
PDF_DIR=./data/pdf
CONFLUENCE_DIR=./data/confluence

# ── Optional: Confluence Integration ─────────────────────
# Leave empty if not using Confluence
CONFLUENCE_URL=
CONFLUENCE_USERNAME=
CONFLUENCE_API_TOKEN=
CONFLUENCE_SPACE_KEY=SRE
```

```bash
# Add .env.example to Git (it's safe — no real secrets)
git add .env.example
git commit -m "Add .env.example template for environment setup"
```

---

## Step 3.3 — Update config.py with Startup Validation

The current `config.py` loads the API key but doesn't validate it — if the key is missing,
you get a confusing error deep inside `rag.py` when Gemini is first called.

The updated version validates at startup so you get a clear error message immediately.

**File: `config.py`** (full content — replace entire file)

```python
# config.py
# ── All project settings in one place ─────────────────────
# Reads from environment variables (set via .env file or system environment).
# Validates critical settings at import time so errors are caught early,
# not buried in a confusing traceback when the first API call fails.

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present (development workflow).
# In production (Azure VM), variables are set directly in the environment
# and this load_dotenv() call simply finds nothing to load — that's fine.
load_dotenv()

# ── API Keys ──────────────────────────────────────────────

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '').strip()

# Validate the key at startup so a missing key surfaces immediately
# with a clear message, rather than as an opaque Gemini API error later.
if not GOOGLE_API_KEY:
    print()
    print("=" * 65)
    print("STARTUP ERROR: GOOGLE_API_KEY is not set")
    print("=" * 65)
    print()
    print("Fix options:")
    print()
    print("  Option 1 — .env file (local development):")
    print("    Edit .env and set: GOOGLE_API_KEY=AIza...")
    print()
    print("  Option 2 — Environment variable (production):")
    print("    export GOOGLE_API_KEY='AIza...'")
    print("    streamlit run app.py")
    print()
    print("Get a key from: https://aistudio.google.com/app/apikey")
    print()
    sys.exit(1)

# Validate key format — Gemini/Google API keys start with 'AIza'
if not GOOGLE_API_KEY.startswith('AIza'):
    print()
    print("=" * 65)
    print("STARTUP ERROR: GOOGLE_API_KEY format looks wrong")
    print("=" * 65)
    print()
    print(f"  Your key starts with: '{GOOGLE_API_KEY[:8]}...'")
    print("  Google API keys start with 'AIza'")
    print()
    print("Check that you copied the full key from Google AI Studio.")
    print()
    sys.exit(1)

# Confluence (optional — only needed if ingesting from Confluence)
CONFLUENCE_URL      = os.getenv('CONFLUENCE_URL', '')
CONFLUENCE_USERNAME = os.getenv('CONFLUENCE_USERNAME', '')
CONFLUENCE_API_TOKEN= os.getenv('CONFLUENCE_API_TOKEN', '')
CONFLUENCE_SPACE_KEY= os.getenv('CONFLUENCE_SPACE_KEY', 'SRE')

# ── Model Settings ────────────────────────────────────────
LLM_MODEL       = os.getenv('LLM_MODEL', 'gemini-flash-latest')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

# ── Document Chunking Settings ────────────────────────────
CHUNK_SIZE    = int(os.getenv('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))

# ── ChromaDB Settings ─────────────────────────────────────
CHROMA_PATH     = os.getenv('CHROMA_PATH', './chroma_db')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'ops_knowledge')

# ── Retrieval Settings ────────────────────────────────────
TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', '5'))

# ── Data Directories ──────────────────────────────────────
MARKDOWN_DIR   = os.getenv('MARKDOWN_DIR', './data/markdown')
PDF_DIR        = os.getenv('PDF_DIR', './data/pdf')
CONFLUENCE_DIR = os.getenv('CONFLUENCE_DIR', './data/confluence')
```

**Key changes in config.py:**
1. Added `GOOGLE_API_KEY.strip()` — removes accidental whitespace/newlines from the env var
2. Added format validation (`startswith('AIza')`) — catches copy-paste errors
3. Added `sys.exit(1)` on validation failure — the app refuses to start with invalid config
4. Moved from hardcoded defaults to env-var-first approach for `LLM_MODEL` and paths

---

## Step 3.4 — Fix .env File Permissions

Your `.env` file is currently world-readable (permissions `644`). On a shared server, any user
on the machine can read it. Fix this:

```bash
cd ~/ops-copilot_gemini

# Restrict to owner read/write only
chmod 600 .env

# Verify:
ls -la .env
# Should show: -rw------- (only owner can read or write)
```

Also fix `users.json` permissions:

```bash
chmod 600 users.json

ls -la users.json
# Should show: -rw------- (only owner can read or write)
```

---

## Step 3.5 — Verify No Secrets in Git History

Check if any sensitive files were committed in the past:

```bash
# Check if .env was ever committed
git log --all --full-history -- .env
# If this shows commits → your API key is in git history. See note below.

# Check if users.json was ever committed  
git log --all --full-history -- users.json
```

**If secrets were previously committed:**

The safest approach for an internal tool is:
1. Rotate the API key immediately (generate a new one in Google AI Studio)
2. Update `.env` with the new key
3. The old key in git history is now invalid

For a truly clean history, you would use `git filter-branch` or BFG Repo Cleaner,
but for an internal team repo, key rotation is simpler and sufficient.

---

## Step 3.6 — Test Configuration Loading

```bash
cd ~/ops-copilot_gemini
source venv/bin/activate

python3 - << 'EOF'
# Test that config.py loads correctly
try:
    from config import GOOGLE_API_KEY, LLM_MODEL, EMBEDDING_MODEL, CHROMA_PATH
    print(f"PASS: GOOGLE_API_KEY loaded (starts with: {GOOGLE_API_KEY[:8]}...)")
    print(f"PASS: LLM_MODEL = {LLM_MODEL}")
    print(f"PASS: EMBEDDING_MODEL = {EMBEDDING_MODEL}")
    print(f"PASS: CHROMA_PATH = {CHROMA_PATH}")
except SystemExit as e:
    print(f"FAIL: config.py exited with code {e.code}")
    print("Check your .env file")
EOF
```

Expected output:
```
PASS: GOOGLE_API_KEY loaded (starts with: AIzaSyDE...)
PASS: LLM_MODEL = gemini-flash-latest
PASS: EMBEDDING_MODEL = all-MiniLM-L6-v2
PASS: CHROMA_PATH = ./chroma_db
```

---

## How This Fits the Application Flow

```
App starts (streamlit run app.py)
          ↓
Python imports config.py at the top of app.py, rag.py, ingest.py
          ↓
config.py: load_dotenv() reads .env file (if present)
          ↓
config.py: os.getenv('GOOGLE_API_KEY') → gets value
          ↓
config.py: validates key is present and starts with 'AIza'
          ↓
  Missing/invalid?          Valid?
       ↓YES                    ↓YES
  print clear error      Config values exported
  sys.exit(1)            as module-level constants
  (app won't start)      rag.py uses GOOGLE_API_KEY
                         to init Gemini client
```

The validation at import time means you get a clear error before any Streamlit UI appears —
much easier to diagnose than a cryptic error when the first query is made.
