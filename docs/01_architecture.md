# 01 — Full System Architecture

> How every piece connects. Read this first — it gives you the mental map for everything else.

---

## The Big Picture in Plain English

Imagine a very smart research assistant who has read every internal document your team has. When you ask a question, they:

1. Search through their memory (the vector database) for the most relevant paragraphs
2. Read those paragraphs carefully
3. Write you a precise answer based only on what they read

That is exactly what this system does — except the "assistant" is Google Gemini, and the "memory" is ChromaDB.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BROWSER (SRE's Laptop)                       │
│                    https://your-server:8501                           │
└──────────────────────────────┬──────────────────────────────────────┘
                                │  HTTPS (encrypted)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT SERVER (app.py)                          │
│                                                                       │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│   │ auth/auth   │    │ auth/session │    │  auth/rate_limiter  │   │
│   │  (login)    │    │  (timeout)   │    │   (throttle)        │   │
│   └──────┬──────┘    └──────┬───────┘    └──────────┬──────────┘   │
│          │                  │                        │               │
│          └──────────────────┴────────────────────────┘               │
│                              │                                        │
│                              ▼                                        │
│                    ┌─────────────────┐                               │
│                    │  core/rag.py   │    ◄── USER'S QUESTION        │
│                    │  (RAG engine)   │                               │
│                    └────────┬────────┘                               │
│                             │                                        │
│            ┌────────────────┴────────────────┐                      │
│            ▼                                  ▼                      │
│   ┌─────────────────┐              ┌──────────────────────┐         │
│   │   ChromaDB      │              │   Google Gemini API  │         │
│   │ (vector search) │              │   (answer writing)   │         │
│   │  ./chroma_db/   │              │   cloud.google.com   │         │
│   └────────┬────────┘              └──────────────────────┘         │
│            │                                                         │
│            │  relevant document chunks                               │
│            └──────────────────────────────────────────────►         │
│                              (context sent to Gemini)                │
│                                                                       │
│   ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐   │
│   │monitoring/   │   │  monitoring/     │   │  auth/           │   │
│   │ logger.py    │   │  audit_log.py    │   │  auth_guard.py   │   │
│   │ (query log)  │   │ (security events)│   │ (page guard)     │   │
│   └──────────────┘   └──────────────────┘   └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ (ONE-TIME SETUP)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 INGESTION PIPELINE (core/ingest.py)                   │
│                                                                       │
│  data/markdown/*.md  ──┐                                             │
│  data/pdf/*.pdf      ──┼──► split into chunks ──► embed ──► ChromaDB│
│  data/yaml/*.yaml    ──┘                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Two Phases of the System

### Phase 1 — Setup (Run Once)

This happens before anyone uses the app. You run `python ingest.py` which:

- Reads all documents from `data/markdown/`, `data/pdf/`, `data/yaml/`
- Splits long documents into smaller pieces (called "chunks")
- Converts every chunk into a 768-number "fingerprint" called a vector/embedding using the BGE base model
- Stores all these fingerprints in ChromaDB on disk

Think of it like building an index for a library. You do it once, and then searches are fast.

### Phase 2 — Runtime (Every User Question)

When a user logs in and asks a question:

1. The question is converted to a vector (same BGE model, with the BGE query prefix)
2. ChromaDB finds the **top 20** chunks whose vectors are most similar to the question vector (wide net, fast)
3. A cross-encoder reranker (`BAAI/bge-reranker-base`) re-scores those 20 chunks by reading each `(question, chunk)` pair directly, and keeps the top 5
4. Those 5 reranked chunks are sent to Gemini as "context"
5. Gemini writes an answer based only on that context
6. The answer streams back word-by-word to the user
7. The question, answer, and latency are logged to the `query_log` table in PostgreSQL

---

## All System Files and Their Roles

```
ops-copilot/
│
├── app.py                   ← Main chat interface (the first page users see)
├── db.py                    ← Shared PostgreSQL connection helper
├── scheduler.py             ← Background auto-ingestion scheduler
├── ingest.py                ← Entry point: runs core/ingest.py
├── evaluate.py              ← Entry point: runs monitoring/evaluate.py
│
├── core/                    ← RAG engine and ingestion
│   ├── config.py            ← All settings (API keys, limits, paths)
│   ├── rag.py               ← Brain — does the search + Gemini call
│   └── ingest.py            ← Document ingestion pipeline
│
├── auth/                    ← Authentication and session management
│   ├── auth.py              ← Login logic + user management (reads from PostgreSQL)
│   ├── auth_guard.py        ← Reusable page protection for dashboards
│   ├── session_manager.py   ← Session timeout tracking (60-min idle, 8-hour max)
│   ├── session_token.py     ← Signed URL-token persistent login (replaces cookies)
│   └── rate_limiter.py      ← API and login throttling
│
├── monitoring/              ← Logging and evaluation
│   ├── audit_log.py         ← Security event logging (writes to audit_log table in PostgreSQL)
│   ├── logger.py            ← Query/usage logging (writes to query_log table in PostgreSQL)
│   └── evaluate.py          ← Measures AI answer quality
│
├── pages/
│   ├── 2_Evaluation_Dashboard.py  ← AI quality scores UI
│   ├── 3_Ingestion_Log.py         ← Document ingestion UI
│   ├── 4_Usage_Dashboard.py       ← Query analytics UI
│   └── 5_Admin_Panel.py           ← User management UI
│
├── data/
│   ├── markdown/            ← Your .md runbooks and docs
│   ├── pdf/                 ← Your PDF documents
│   └── yaml/                ← Your Kubernetes YAML files
│
├── db/
│   └── init.sql             ← PostgreSQL schema initialisation
│
├── tests/
│   ├── test_ingest.py
│   └── test_rag.py
│
├── scripts/
│   └── migration.py
│
├── chroma_db/               ← Where vectors are stored on disk
├── certs/                   ← TLS certificates for HTTPS
│   ├── cert.pem
│   └── key.pem
│
└── .env                     ← Secret keys (never commit this to Git!)
```

---

## How the Files Talk to Each Other

```
app.py
  │
  ├── imports auth.auth           (to handle login)
  ├── imports core.rag            (to answer questions)
  ├── imports monitoring.logger   (to log every query)
  ├── imports auth.session_manager (to check session timeout)
  └── imports auth.rate_limiter   (to block too-fast queries)

auth/auth.py
  │
  ├── imports auth.rate_limiter   (to check login attempt count)
  └── imports monitoring.audit_log (to log login success/failure)

pages/2_Evaluation_Dashboard.py
pages/3_Ingestion_Log.py
pages/4_Usage_Dashboard.py
pages/5_Admin_Panel.py
  │
  └── all import auth.auth_guard  (to enforce login on every page)

auth/auth_guard.py
  │
  ├── imports auth.auth           (for check_login)
  └── imports auth.session_manager (for session check)
```

---

## Data Flow for a Single Question

Here is what happens in sequence when a user types "What version is CustomerX running?":

```
User types question in browser
        │
        ▼
app.py receives the text via st.chat_input()
        │
        ├─► rate_limiter.check_query_rate_limit(user)
        │       └── returns (True, "") if allowed
        │           returns (False, msg) if blocked → show error → stop
        │
        ├─► rag.ask_stream(question, customer_scope=None)
        │       │
        │       ├─► embedder.encode("Represent this sentence for searching relevant passages: " + question)
        │       │       └── converts question to a 768-number vector (BGE base)
        │       │
        │       ├─► collection.query(question_vector, n_results=20)
        │       │       └── ChromaDB returns top 20 candidate chunks (wide net)
        │       │
        │       ├─► reranker.predict([(question, chunk), ...])
        │       │       └── BGE cross-encoder re-scores all 20 pairs,
        │       │           top 5 are kept for the LLM
        │       │
        │       ├─► builds "context" string from those 5 reranked chunks
        │       │
        │       └─► client.models.generate_content_stream(prompt_with_context)
        │               └── Gemini streams answer tokens back
        │                   each token is yielded to st.write_stream()
        │                   the user sees text appearing word by word
        │
        ├─► logger.log_query(username, question, answer, sources, latency_ms)
        │       └── inserts row into PostgreSQL `query_log` table
        │
        └─► answer + sources are saved to st.session_state.messages
                └── next rerun shows them in chat history
```

---

## The Three Security Layers

| Layer | Who Stops It | What It Stops |
|-------|-------------|---------------|
| Authentication | auth/auth.py + auth/auth_guard.py | Unauthenticated users seeing any page |
| Session timeout | auth/session_manager.py | Abandoned logged-in sessions |
| Rate limiting | auth/rate_limiter.py | Brute-force attacks + API abuse |

All three run on every page load before any content is shown.
