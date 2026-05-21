# 10 — Presentation Guide for the SRE Team

> Use this as your speaker notes. Each section maps to a part of your demo.

---

## Opening: What Problem Does This Solve?

> **Say this:** "Every time one of us gets a customer escalation, the first 10 minutes is spent digging through folders, Confluence pages, and Slack history to find the right runbook. This tool eliminates that. You ask in English, it finds the answer in our own documents."

**Key points to hit:**
- Internal knowledge base — not a general AI
- Answers are grounded in YOUR documents, not the internet
- Every answer shows which document it came from
- Works for all customer runbooks and architecture docs

---

## Demo Flow (Live Walk-Through)

### Step 1: Show the Login

Navigate to the app. Show the login form.

> **Say:** "Access is gated by authentication. Passwords are never stored in plain text — they're hashed with bcrypt, which is the same algorithm banks use."

Log in as `alice` or `chalaka`.

### Step 2: Show the Chat

Ask a live question:
```
What version is CustomerX running?
```

Watch the answer stream word by word.

> **Say:** "Notice the answer appears word by word — that's real-time streaming from Google's Gemini API. Below the answer, you can see exactly which documents it pulled from, with a similarity percentage."

### Step 3: Explain RAG (One Sentence)

> **Say:** "Under the hood, when you ask a question, three things happen: your question is converted into a mathematical vector, ChromaDB finds the 5 document chunks most similar to that vector, and those chunks are sent to Gemini as context. Gemini writes the answer from those chunks only."

### Step 4: Navigate to Evaluation Dashboard

Click "Evaluation Dashboard" in the sidebar.

> **Say:** "We have automated quality measurement. Every week we can run an evaluation that checks two things: Is Gemini sticking to what our documents actually say? — that's Faithfulness. And is it actually answering the question? — that's Answer Relevancy. We're targeting 85% and 80% respectively."

### Step 5: Navigate to Usage Dashboard

Click "Usage Dashboard".

> **Say:** "This shows us operational data — how many queries per day, who's using it most, what documents get retrieved most, and average response time. This helps us understand what the team is actually looking up and whether our knowledge base is complete."

### Step 6: Navigate to Admin Panel (if logged in as admin)

Click "Admin Panel".

> **Say:** "Admins can create and remove user accounts directly from the web interface. No editing config files. When a new SRE joins, we add them here — access is immediate."

---

## Technical Questions Your Team May Ask

### "Is this sending our customer data to Google?"

**Answer:** Yes, document chunks (excerpts) are sent to the Gemini API as context when answering a question. The API key is ours — Google doesn't use API data for training by default under enterprise terms. For highly sensitive data, you'd want to run a local LLM instead of Gemini.

The embedding model (`BAAI/bge-base-en-v1.5`) and the reranker (`BAAI/bge-reranker-base`) both run completely locally — your documents are converted to vectors and reranked on your own machine, no data sent anywhere for those steps.

### "What happens if Gemini is down?"

**Answer:** The app shows an error to the user. No crash, no data loss. The error is recorded in the `query_log` table in PostgreSQL with `success = false` and the error message. The vector database and your documents are unaffected — you just can't get AI answers until Gemini recovers.

### "Can it read from Confluence directly?"

**Answer:** Yes — the `ingest.py` script has a `load_confluence_documents()` function that connects to Confluence via API token. We just need to fill in the `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, and `CONFLUENCE_API_TOKEN` in the `.env` file. The Streamlit version needs these set before running `python ingest.py`.

### "How do we add new runbooks?"

**Answer:** Drop the `.md` file into `data/markdown/`. Name it with the customer name in the filename (e.g., `customerZ_runbook.md`). Then run `python ingest.py`. It appears in the knowledge base immediately.

### "What's the rate limit for?"

**Answer:** Two reasons. First, the Gemini free tier allows 15 requests per minute — if the whole team floods the API simultaneously, everyone gets errors. The per-user limit (10/minute) prevents one person from blocking everyone else. Second, it stops someone from accidentally (or deliberately) running a loop that burns through API quota.

### "Is this production-ready?"

**Answer:** For an internal team tool with ~50 WSO2 engineers and 30–40 concurrent users, yes. Users, audit log, and query log are already in PostgreSQL. Streamlit runs in Docker behind HTTPS. For an external-facing deployment or significantly higher load, you'd want: a proper SIEM that ingests from the `audit_log` table, a secrets manager instead of `.env`, a reverse proxy like nginx in front of Streamlit, and the rate-limit counters moved from in-memory dicts to Redis or postgres so they survive container restarts.

### "Can we use this for CustomerZ runbooks too?"

**Answer:** They're already ingested. The ingestion pipeline reads all files in `data/markdown/`. `customerZ_architecture.md` and `customerZ_runbook.md` are in there. Just ask about CustomerZ.

---

## Architecture Summary (One Slide)

```
SRE Types Question
       │
       ▼
Streamlit Web App (app.py, running in Docker)
  ├── URL-token restore (auth/session_token.py)
  ├── Login check (auth/auth.py + bcrypt, reads PostgreSQL)
  ├── Session check (60 min idle + 8 hour max)
  └── Rate limit check (10 queries/min, 100/hr)
       │
       ▼
RAG Engine (core/rag.py)
  ├── Embed question with BGE base (768-dim, runs locally)
  ├── ChromaDB top-20 vector search (wide net)
  ├── BGE cross-encoder rerank → top 5 (precise)
  ├── Build prompt: system instructions + chunks + question
  └── Call Gemini API → stream answer
       │
       ▼
PostgreSQL: audit_log table + query_log table
```

---

## Security Summary (One Slide)

| Layer | Technology | Protects Against |
|-------|-----------|-----------------|
| Transport | HTTPS/TLS | Network eavesdropping |
| Auth | bcrypt passwords | Weak/cracked passwords |
| Login throttle | 5 attempts/hour | Brute force |
| Session timeout | 60 min inactive, 8 hr max | Abandoned sessions |
| Query throttle | 10/min, 100/hr | API cost explosion |
| Audit log | `audit_log` table (PostgreSQL) | Post-incident investigation |
| Page guard | auth/auth_guard.py | Unauthenticated page access |
| Role check | Admin Panel | Privilege escalation |

---

## Numbers to Know

| Metric | Value |
|--------|-------|
| Knowledge chunks in database | varies after ingestion (see Ingestion Log page) |
| Max queries per minute per user | 10 |
| Max queries per hour per user | 100 |
| Failed logins before lockout | 5 per hour |
| Session inactivity timeout | 60 minutes (resets on every refresh / interaction) |
| Maximum session length | 8 hours (NOT reset on refresh — counts from original login) |
| Persistent-login URL token lifetime | 7 days |
| Stage-1 vector-search candidates | 20 |
| Final chunks retrieved per question | 5 (after reranking) |
| Chunk size | 1000 characters (~200 words) |
| Chunk overlap | 200 characters |
| Embedding dimensions | 768 (BGE base) |
| bcrypt cost factor | 12 (4096 iterations) |
| Target faithfulness score | > 85% |
| Target answer relevancy score | > 80% |
