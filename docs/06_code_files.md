# 06 — Every Python File Explained

> What each file does, why it exists, and how it fits into the system.

---

## core/config.py — Central Settings Store

**File:** [core/config.py](../core/config.py)  
**Purpose:** One place to change settings without hunting through multiple files.

```python
import os
from dotenv import load_dotenv
load_dotenv()   # reads .env file into environment variables

GOOGLE_API_KEY   = os.getenv('GOOGLE_API_KEY')     # Gemini API key
LLM_MODEL        = 'gemini-flash-latest'           # which Gemini model to use
EMBEDDING_MODEL  = 'all-MiniLM-L6-v2'             # local embedding model name
CHUNK_SIZE       = 1000                            # characters per document chunk
CHUNK_OVERLAP    = 200                             # overlap between adjacent chunks
CHROMA_PATH      = './chroma_db'                   # folder for vector database
COLLECTION_NAME  = 'ops_knowledge'                 # name of the ChromaDB collection
TOP_K_RESULTS    = 5                               # how many chunks to retrieve per query
MARKDOWN_DIR     = './data/markdown'               # where markdown docs live
PDF_DIR          = './data/pdf'                    # where PDF docs live
```

**How other files use it:**
```python
# Every other Python file imports from core/config.py:
from core.config import GOOGLE_API_KEY, LLM_MODEL, CHROMA_PATH, ...
```

**Changing settings:** Edit `core/config.py` and restart the app. For secrets (API keys), change the `.env` file instead — `core/config.py` reads from it.

---

## app.py — Main Chat Interface

**File:** [app.py](../app.py)  
**Purpose:** The first page users see. Handles login, the chat UI, and orchestrates the RAG call.  
**Lines:** 313  
**Run with:** `streamlit run app.py`

### Structure (Top to Bottom)

```
Lines 1-20:    Imports + st.set_page_config (MUST be first Streamlit call)
Lines 26-59:   Session state init + Login gate
Lines 61-80:   Session timeout check
Lines 84-100:  Custom CSS (source chip styling)
Lines 102-155: Sidebar (user info, sign out, session timer, suggested questions)
Lines 157-178: Main header + captions
Lines 184-200: Chat history display loop
Lines 220-231: Handle pre-filled questions (from sidebar buttons)
Lines 234-246: Rate limit check
Lines 249-311: RAG call with streaming + logging
```

### Key Logic: The Login Gate

```python
if not st.session_state.authenticated:
    # Show login form
    if submit:
        user_info = check_login(username, password)
        if user_info:
            st.session_state.authenticated = True
            init_session_tracking()
            st.rerun()
    st.stop()   # ← nothing below runs for unauthenticated users
```

### Key Logic: The Chat Loop

```python
for msg in st.session_state.messages:   # replay all history
    with st.chat_message(msg['role']):
        st.write(msg['content'])
        if msg['role'] == 'assistant' and msg.get('sources'):
            # show source citations
```

### Key Logic: Sending a Query

```python
if prompt:
    # 1. Check rate limit
    query_allowed, rate_message = check_query_rate_limit(current_user)
    if not query_allowed:
        st.error(rate_message)
        st.stop()
    
    # 2. Show user's message
    with st.chat_message('user'):
        st.write(prompt)
    
    # 3. Stream the answer
    with st.chat_message('assistant'):
        full_answer = st.write_stream(text_only_stream())  # word by word
    
    # 4. Log the query
    log_query(username, question, sources, latency_ms, success)
    
    # 5. Save to history
    st.session_state.messages.append({...})
```

---

## core/rag.py — The Brain: RAG Engine

**File:** [core/rag.py](../core/rag.py)  
**Purpose:** Embeds questions, searches ChromaDB, calls Gemini, streams answers.  
**Lines:** 264

### Module-Level Initialization (Runs Once at Import)

```python
# These run when Python first imports core/rag.py (at app startup)
client   = genai.Client(api_key=GOOGLE_API_KEY)          # Gemini connection
embedder = SentenceTransformer(EMBEDDING_MODEL)           # load embedding model (~80MB)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)  # connect to ChromaDB
collection = chroma_client.get_or_create_collection(...)  # get the chunk collection
```

Loading these takes a few seconds on startup. After that, they stay in memory — no reload per query.

### ask() — Synchronous Version

Returns `(answer_string, sources_list)` all at once. Not used for the main chat (we use streaming instead), but used by `monitoring/evaluate.py` for testing.

```python
def ask(question, customer_scope):
    question_embedding = embedder.encode(question).tolist()
    results = collection.query(query_embeddings=[...], n_results=5, ...)
    context = build_context_string(results)
    prompt = system_prompt + context + question
    response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
    return response.text, sources
```

### ask_stream() — Streaming Version

A Python generator that yields text pieces one at a time. Used by app.py for the word-by-word streaming effect.

```python
def ask_stream(question, customer_scope):
    # ... same retrieval as ask() ...
    
    response = client.models.generate_content_stream(...)
    
    for chunk in response:     # Gemini sends text in small pieces
        if chunk.text:
            yield chunk.text   # each piece goes to browser immediately
    
    yield sources              # at the very end, yield sources list
```

The `yield sources` at the end is a trick: app.py checks whether each yielded value is a `list` (sources) or a `str` (text). Sources are collected separately from the text.

---

## core/ingest.py — Document Ingestion Pipeline

**File:** [core/ingest.py](../core/ingest.py)  
**Purpose:** One-time (or periodic) script to load documents into ChromaDB.  
**Run with:** `python ingest.py`

### The Pipeline

```
load_markdown_documents()  → List[Document]
load_pdf_documents()       → List[Document]
load_yaml_documents()      → List[Document]
         │
         ▼
add_customer_metadata(all_docs)    → adds 'customer' and 'doc_type' to metadata
         │
         ▼
split_documents(all_docs)          → List[Chunk] (many smaller pieces)
         │
         ▼
store_in_chromadb(chunks)          → computes embeddings, upserts to ChromaDB
         │
         ▼
save_ingestion_state(state)        → records file hashes to ingestion_state.json
```

### File Hash Tracking

```python
def file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
```

After ingestion, each file's MD5 hash is stored in `ingestion_state.json`. The Ingestion Log page shows this table — you can see which files have been ingested and whether they still exist.

---

## auth/auth.py — Authentication Logic

**File:** [auth/auth.py](../auth/auth.py)  
**Purpose:** All user authentication: verify passwords, create users, delete users.  
**Lines:** 336

### Functions

| Function | Purpose |
|----------|---------|
| `load_users()` | Read users.json, return the `users` dict |
| `hash_password(password)` | bcrypt hash a plain-text password → 60-char string |
| `verify_password(password, stored_hash)` | Check plain-text against bcrypt hash → True/False |
| `check_login(username, password)` | Full login flow with rate limiting and audit logging |
| `get_user_customers(username)` | Get list of customers a user can access |
| `create_user(...)` | Hash password and add to users.json |
| `delete_user(username)` | Remove from users.json |

### The Most Important Detail

`check_login()` always returns the same error message to the UI (`st.error('Incorrect username or password.')`) regardless of whether:
- The username doesn't exist
- The password is wrong
- The account is rate-limited

This is intentional security design — never tell an attacker which part of their attempt was wrong.

---

## auth/auth_guard.py — Reusable Page Protection

**File:** [auth/auth_guard.py](../auth/auth_guard.py)  
**Purpose:** One function that every dashboard page calls to enforce authentication.  
**Lines:** 57

```python
def require_authentication() -> dict:
    # Check login → stop if not authenticated
    # Check session → stop if expired
    # Show logout button in sidebar
    # Return user_info if all OK
```

**Why have a separate file?** Without it, every dashboard page would need 20+ lines of auth checking code, all identical. If we wanted to change the auth logic (e.g., add 2FA), we'd need to update 4 files. With auth/auth_guard.py, we update one function.

This is the software engineering principle of **Don't Repeat Yourself (DRY)**.

---

## auth/session_manager.py — Session Timeout Tracking

**File:** [auth/session_manager.py](../auth/session_manager.py)  
**Purpose:** Track when users last interacted and log them out when inactive.  
**Lines:** 191

### Functions

| Function | Purpose |
|----------|---------|
| `init_session_tracking()` | Called at login. Sets `last_activity` and `session_start` in session_state. |
| `check_session_timeout()` | Called on every page load. Returns (True, "") or (False, message). |
| `logout_user()` | Clears all session_state keys. |
| `get_session_info()` | Returns timing data for sidebar display (optional). |
| `display_session_status()` | Shows collapsible "Session Info" in sidebar. |

### The Heartbeat Mechanism

Every time `check_session_timeout()` is called and the session is still valid, it updates `last_activity`:

```python
# Session is valid — update last_activity (this is the heartbeat)
st.session_state.last_activity = now
return True, ""
```

Every page interaction (clicking, typing, submitting) causes a rerun, which calls `check_session_timeout()`, which updates `last_activity`. So as long as the user keeps interacting, the inactivity clock resets. Only true inactivity (60 minutes of nothing) triggers logout.

---

## auth/rate_limiter.py — Throttling

**File:** [auth/rate_limiter.py](../auth/rate_limiter.py)  
**Purpose:** Prevent API cost explosions and brute-force attacks.  
**Lines:** 191

### In-Memory Storage

```python
_query_timestamps: dict = defaultdict(list)
_failed_login_timestamps: dict = defaultdict(list)
```

`defaultdict(list)` is a Python dictionary that automatically creates an empty list for any new key. When you access `_query_timestamps['newuser']`, instead of raising a `KeyError`, it creates `{'newuser': []}`.

### Functions

| Function | Purpose |
|----------|---------|
| `check_query_rate_limit(username)` | Before each RAG query. Returns (True,"") or (False,msg). |
| `check_login_rate_limit(username)` | Before each login attempt. Returns (True,"") or (False,msg). |
| `record_failed_login(username)` | Adds timestamp to `_failed_login_timestamps[username]`. |
| `reset_login_attempts(username)` | Clears `_failed_login_timestamps[username]` after successful login. |
| `get_rate_limit_status(username)` | Returns a dict of counters (for admin/debug). |

---

## monitoring/audit_log.py — Security Event Journal

**File:** [monitoring/audit_log.py](../monitoring/audit_log.py)  
**Purpose:** Append-only log of all security-relevant events.  
**Lines:** 174

### Functions

| Function | Purpose |
|----------|---------|
| `log_security_event(event_type, username, details, ...)` | Append one record to audit_log.json (atomic write). |
| `get_failed_logins_last_n_minutes(minutes)` | Return LIST of LOGIN_FAILED events in the last N minutes. |
| `get_user_audit_trail(username, limit)` | Return last N events for a specific user. |

### Event Type Constants (At Module Level)

```python
LOGIN_SUCCESS    = 'LOGIN_SUCCESS'
LOGIN_FAILED     = 'LOGIN_FAILED'
LOGOUT           = 'LOGOUT'
SESSION_EXPIRED  = 'SESSION_EXPIRED'
USER_CREATED     = 'USER_CREATED'
USER_DELETED     = 'USER_DELETED'
QUERY_EXECUTED   = 'QUERY_EXECUTED'
RATE_LIMIT_HIT   = 'RATE_LIMIT_HIT'
```

Using constants (not raw strings) means a typo like `'LOGON_SUCCESS'` would be caught as a `NameError` at import time — rather than silently writing a wrong event type to the log.

---

## monitoring/logger.py — Query Usage Logger

**File:** [monitoring/logger.py](../monitoring/logger.py)  
**Purpose:** Record every RAG query for analytics and debugging.  
**Lines:** 120

### Functions

| Function | Purpose |
|----------|---------|
| `log_query(username, question, sources, latency_ms, ...)` | Append query record to query_log.json. |
| `load_log()` | Read all query records for the Usage Dashboard. |

### Why Separate from monitoring/audit_log.py?

The audit log is for **security events** — who logged in, who was blocked, who was created. It needs to be tamper-evident and reviewed for security incidents.

The query log is for **operational metrics** — how many queries, how fast, what's popular. It's analyzed for performance optimization and usage patterns.

Mixing them would make both harder to analyze. Keeping them separate follows the "single responsibility" principle.

---

## monitoring/evaluate.py — RAG Quality Measurement

**File:** [monitoring/evaluate.py](../monitoring/evaluate.py)  
**Purpose:** Run automated tests to measure how accurate the AI answers are.  
**Run with:** `python evaluate.py`

### What It Does

1. Runs 5 predefined test questions through the RAG system
2. Uses the RAGAS library to score each answer on two metrics
3. Saves scores to `evaluation_results.json`
4. The Evaluation Dashboard reads that file and displays the scores

### The Two Metrics

**Faithfulness:** Does Gemini's answer stick to the retrieved documents, or does it make things up?
- Score of 1.0 = everything said is supported by the context
- Score of 0.5 = half the claims are in the context, half are hallucinated

**Answer Relevancy:** Does the answer actually address the question?
- Score of 1.0 = answer is directly relevant to the question
- Score of 0.5 = answer talks about related topics but doesn't answer the question

### Target Scores

- Faithfulness: > 0.85 (85%)
- Answer Relevancy: > 0.80 (80%)

---

## scripts/migration.py — SHA-256 to bcrypt Migration Script

**File:** [scripts/migration.py](../scripts/migration.py)  
**Purpose:** One-time migration script for upgrading passwords from SHA-256 to bcrypt.  
**Status:** Already run — all users in users.json now have bcrypt hashes.

This script was used to migrate from the old insecure SHA-256 hashing to the current bcrypt hashing. It is kept for reference but should not need to be run again.

---

## scheduler.py — Background Task Scheduler

**File:** [scheduler.py](../scheduler.py)  
**Purpose:** Run periodic background tasks (e.g., scheduled re-ingestion).  
**Technology:** APScheduler library

This is a utility for scheduling automatic document re-ingestion (e.g., every night at 2am, re-ingest all documents). It uses the `APScheduler` library listed in `requirements.txt`.
