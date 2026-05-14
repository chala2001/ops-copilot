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
│   │  auth.py    │    │ session_mgr  │    │   rate_limiter.py   │   │
│   │  (login)    │    │  (timeout)   │    │   (throttle)        │   │
│   └──────┬──────┘    └──────┬───────┘    └──────────┬──────────┘   │
│          │                  │                        │               │
│          └──────────────────┴────────────────────────┘               │
│                              │                                        │
│                              ▼                                        │
│                    ┌─────────────────┐                               │
│                    │    rag.py       │    ◄── USER'S QUESTION        │
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
│   │  logger.py   │   │  audit_log.py    │   │  auth_guard.py   │   │
│   │ (query log)  │   │ (security events)│   │ (page guard)     │   │
│   └──────────────┘   └──────────────────┘   └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ (ONE-TIME SETUP)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE (ingest.py)                     │
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
- Converts every chunk into a 384-number "fingerprint" called a vector/embedding
- Stores all these fingerprints in ChromaDB on disk

Think of it like building an index for a library. You do it once, and then searches are fast.

### Phase 2 — Runtime (Every User Question)

When a user logs in and asks a question:

1. The question is converted to a vector (same method as the documents)
2. ChromaDB finds the 5 chunks whose vectors are most similar to the question vector
3. Those 5 chunks are sent to Gemini as "context"
4. Gemini writes an answer based only on that context
5. The answer streams back word-by-word to the user
6. The question, answer, and latency are logged

---

## All System Files and Their Roles

```
ops-copilot_gemini/
│
├── app.py                   ← Main chat interface (the first page users see)
├── config.py                ← All settings (API keys, limits, paths)
├── rag.py                   ← Brain — does the search + Gemini call
├── ingest.py                ← One-time document loader
├── evaluate.py              ← Measures AI answer quality
│
├── auth.py                  ← Login logic + user management functions
├── auth_guard.py            ← Reusable page protection for dashboards
├── session_manager.py       ← Session timeout tracking
├── rate_limiter.py          ← API and login throttling
├── audit_log.py             ← Security event logging
├── logger.py                ← Query/usage logging
│
├── users.json               ← User accounts (bcrypt hashed passwords)
├── audit_log.json           ← Security events (auto-generated)
├── query_log.json           ← Query history (auto-generated)
├── ingestion_state.json     ← Which files have been ingested
├── evaluation_results.json  ← Last AI quality score
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
  ├── imports auth.py           (to handle login)
  ├── imports rag.py            (to answer questions)
  ├── imports logger.py         (to log every query)
  ├── imports session_manager.py (to check session timeout)
  └── imports rate_limiter.py   (to block too-fast queries)

auth.py
  │
  ├── imports rate_limiter.py   (to check login attempt count)
  └── imports audit_log.py     (to log login success/failure)

pages/2_Evaluation_Dashboard.py
pages/3_Ingestion_Log.py
pages/4_Usage_Dashboard.py
pages/5_Admin_Panel.py
  │
  └── all import auth_guard.py  (to enforce login on every page)

auth_guard.py
  │
  ├── imports auth.py           (for check_login)
  └── imports session_manager.py (for session check)
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
        │       ├─► embedder.encode(question)
        │       │       └── converts question to a 384-number vector
        │       │
        │       ├─► collection.query(question_vector, n_results=5)
        │       │       └── ChromaDB finds 5 most similar document chunks
        │       │
        │       ├─► builds "context" string from those 5 chunks
        │       │
        │       └─► client.models.generate_content_stream(prompt_with_context)
        │               └── Gemini streams answer tokens back
        │                   each token is yielded to st.write_stream()
        │                   the user sees text appearing word by word
        │
        ├─► logger.log_query(username, question, answer, sources, latency_ms)
        │       └── appends to query_log.json
        │
        └─► answer + sources are saved to st.session_state.messages
                └── next rerun shows them in chat history
```

---

## The Three Security Layers

| Layer | Who Stops It | What It Stops |
|-------|-------------|---------------|
| Authentication | auth.py + auth_guard.py | Unauthenticated users seeing any page |
| Session timeout | session_manager.py | Abandoned logged-in sessions |
| Rate limiting | rate_limiter.py | Brute-force attacks + API abuse |

All three run on every page load before any content is shown.
