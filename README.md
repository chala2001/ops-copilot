# SRE Ops Copilot

**AI-Powered RAG Knowledge Base for Enterprise SRE Teams**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-Flash-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-orange?style=flat)](https://trychroma.com)
[![HTTPS](https://img.shields.io/badge/HTTPS-Enabled-green?style=flat)](https://letsencrypt.org)

> An intelligent assistant that lets Site Reliability Engineering teams ask natural-language questions about customer deployments, infrastructure configurations, and runbooks — and get instant, source-cited answers grounded in internal documentation.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [System Architecture](#system-architecture)
- [RAG Pipeline](#rag-pipeline)
- [Security Architecture](#security-architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Document Ingestion](#document-ingestion)
- [Security Features](#security-features)
- [Pages and Dashboards](#pages-and-dashboards)
- [Testing](#testing)
- [Deployment](#deployment)
- [What I Learned](#what-i-learned)

---

## Overview

SRE Ops Copilot is a Retrieval-Augmented Generation (RAG) system built for enterprise SRE teams managing multiple customer environments. Engineers ask questions in plain English and get answers grounded exclusively in internal documentation — with full source citations showing exactly which document the answer came from.

This project was built as a first internship project to demonstrate production-grade AI application development, including multi-layer security, streaming responses, RAG evaluation pipelines, and enterprise deployment readiness.

---

## Problem Statement

```
WITHOUT this tool                          WITH this tool
─────────────────────────────────────────────────────────────────
"What version is CustomerX running?"       Ask the chat → answer in 2 seconds
→ Search Confluence (3 min)                with source citations
→ Check Slack history (5 min)
→ Ask a senior engineer (10 min)           "Who do I call for a CustomerZ P1?"
→ Total: 15-20 minutes per question        → Instant answer with contact details

Knowledge siloed with individuals          Knowledge centralised and searchable
New joiners need weeks to onboard          Runbooks accessible from day one
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                              │
│                    https://localhost:8501                           │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTPS / TLS
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT APPLICATION                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   app.py     │  │ Evaluation   │  │  Ingestion   │             │
│  │  (Chat UI)   │  │  Dashboard   │  │     Log      │             │
│  └──────┬───────┘  └──────────────┘  └──────────────┘             │
│         │           ┌──────────────┐  ┌──────────────┐             │
│         │           │    Usage     │  │ Admin Panel  │             │
│         │           │  Dashboard   │  │  (Users)     │             │
│         │           └──────────────┘  └──────────────┘             │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    SECURITY LAYER                          │    │
│  │  auth.py (bcrypt)  │  session_manager.py  │  rate_limiter  │   │
│  │  audit_log.py      │  auth_guard.py        │               │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RAG ENGINE  (rag.py)                         │
│                                                                     │
│   Question ──► Embed ──► ChromaDB Search ──► Build Context         │
│                                                  │                  │
│                                                  ▼                  │
│                                           Google Gemini API         │
│                                        (streaming response)         │
│                                                  │                  │
│                                                  ▼                  │
│                                    Answer  +  Source Citations      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌───────────┐      ┌─────────────┐
│ ChromaDB  │      │ Gemini API  │
│  Vector   │      │    (LLM)    │
│   Store   │      └─────────────┘
└─────┬─────┘
      │  populated by ingest.py
      ▼
┌─────────────────────────────────┐
│          DATA SOURCES           │
│  Markdown   YAML    PDF         │
│  Runbooks   K8s     Guides      │
│             Configs             │
│         Confluence Pages        │
└─────────────────────────────────┘
```

---

## RAG Pipeline

RAG (Retrieval-Augmented Generation) is the core technique. Instead of relying on a model's training data, the system retrieves relevant internal documents first, then asks the LLM to answer using only that retrieved content.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PHASE 1 — INGESTION  (run once: python ingest.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Raw Documents (.md / .yaml / .pdf / Confluence)
       │
       ▼
  LangChain Loaders
  (DirectoryLoader, PyPDFLoader, ConfluenceLoader, GitLoader)
       │
       ▼
  Text Splitter
  chunk_size=1000 chars, chunk_overlap=200 chars
       │
       ▼
  SentenceTransformer  (all-MiniLM-L6-v2, runs locally)
  Text  ──────────────────────►  384-dimensional vector
       │
       ▼
  ChromaDB  (cosine similarity index, persisted to disk)
  Stores: vector + document text + metadata (source, customer)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PHASE 2 — QUERY  (real-time, every question)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  User Question
       │
       ▼
  SentenceTransformer  →  question vector
       │
       ▼
  ChromaDB  →  Top-5 chunks by cosine similarity
       │
       ▼
  Context Builder
  [Source 1: file.md | Customer: CustomerX]
  <chunk text>
  [Source 2: config.yaml | Customer: CustomerY]
  <chunk text>  ...
       │
       ▼
  Google Gemini Flash
  generate_content_stream()  →  streaming token output
       │
       ▼
  Answer + Source Chips  displayed in browser

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Why RAG instead of fine-tuning?**

| Approach | Update docs | Cost | Hallucination risk |
|---|---|---|---|
| Fine-tuning | Retrain model | Very high ($$$) | High |
| RAG (this project) | Re-run ingest.py | Near zero | Low — answers grounded in docs |

---

## Security Architecture

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SECURITY LAYERS — DEFENCE IN DEPTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Layer 1 — Transport Security
  ┌────────────────────────────────────────────────┐
  │  HTTPS / TLS (cert.pem + key.pem)              │
  │  Self-signed for dev, Let's Encrypt for prod   │
  │  Configured in .streamlit/config.toml          │
  └────────────────────────────────────────────────┘
            │
  Layer 2 — Authentication
  ┌────────────────────────────────────────────────┐
  │  bcrypt  (cost factor 12, ~100ms per hash)     │
  │  Constant-time comparison — timing-safe        │
  │  users.json — zero plaintext passwords         │
  └────────────────────────────────────────────────┘
            │
  Layer 3 — Session Management
  ┌────────────────────────────────────────────────┐
  │  60-minute inactivity timeout                  │
  │  8-hour absolute session cap                   │
  │  auth_guard.py — enforced on every page        │
  └────────────────────────────────────────────────┘
            │
  Layer 4 — Rate Limiting
  ┌────────────────────────────────────────────────┐
  │  Queries:  10 / min,  100 / hour  per user     │
  │  Logins:   5 failed attempts / hour lockout    │
  │  Sliding window algorithm (in-memory)          │
  └────────────────────────────────────────────────┘
            │
  Layer 5 — Audit Logging
  ┌────────────────────────────────────────────────┐
  │  audit_log.json — all security events          │
  │  Atomic writes (temp file → rename)            │
  │  Events: LOGIN, LOGOUT, FAILED, RATE_LIMIT     │
  │  query_log.json — every question + latency     │
  └────────────────────────────────────────────────┘
```

---

## Features

### Core Functionality
- **Natural language Q&A** — plain English questions, no query language needed
- **Streaming responses** — answers appear word-by-word in real time
- **Source citations** — every answer links to the exact source document and similarity score
- **Multi-format ingestion** — Markdown, YAML, PDF, Confluence, GitHub repos
- **Customer-aware tagging** — documents tagged by customer for traceability

### Security
- **bcrypt password hashing** — industry-standard, replaced SHA-256
- **HTTPS** — encrypted transport with TLS certificates
- **Session timeout** — auto-logout after 60 min inactivity
- **Rate limiting** — prevents API abuse and brute-force
- **Audit trail** — every login, logout, and failure recorded to disk

### Dashboards
- **Usage Dashboard** — queries per day, latency distribution, per-user counts
- **Evaluation Dashboard** — RAGAS quality scoring (faithfulness, relevancy, precision)
- **Ingestion Log** — document tracking, hash change detection, one-click re-ingest
- **Admin Panel** — create/delete users with bcrypt hashing automatically applied

---

## Tech Stack

| Category | Technology | Role |
|---|---|---|
| UI Framework | Streamlit 1.57 | Multi-page web application |
| LLM | Google Gemini Flash | Answer generation |
| Embedding | all-MiniLM-L6-v2 | Local text-to-vector (no API cost) |
| Vector DB | ChromaDB (persistent) | Semantic similarity search |
| Document Loading | LangChain Community | Markdown, PDF, YAML, Confluence |
| Text Splitting | RecursiveCharacterTextSplitter | 1000-char chunks, 200 overlap |
| Password Hashing | bcrypt cost=12 | Authentication |
| RAG Evaluation | RAGAS | Answer quality scoring |
| Scheduling | APScheduler | Automated re-ingestion |
| TLS | OpenSSL / Let's Encrypt | HTTPS |
| Containerisation | Docker + docker-compose | Deployment packaging |

---

## Project Structure

```
ops-copilot_gemini/
│
├── app.py                      # Main chat UI — entry point
│
├── rag.py                      # RAG engine: embed → search → generate
├── ingest.py                   # Document ingestion pipeline
├── config.py                   # Centralised settings
├── auth.py                     # bcrypt authentication
├── auth_guard.py               # Session check shared by all pages
├── session_manager.py          # Inactivity/absolute timeout tracking
├── rate_limiter.py             # Sliding window rate limiting
├── audit_log.py                # Security event logging
├── logger.py                   # Query logging (latency, sources)
├── evaluate.py                 # RAGAS evaluation runner
├── scheduler.py                # Automated re-ingestion scheduler
│
├── pages/
│   ├── 2_Evaluation_Dashboard.py   # RAG quality metrics
│   ├── 3_Ingestion_Log.py          # Document status + re-ingest
│   ├── 4_Usage_Dashboard.py        # Query analytics
│   └── 5_Admin_Panel.py            # User management
│
├── data/
│   ├── markdown/               # Runbooks and architecture docs
│   ├── yaml/                   # Kubernetes deployment configs
│   ├── pdf/                    # PDF documents
│   └── confluence/             # Confluence page exports
│
├── .streamlit/config.toml      # HTTPS and server configuration
├── certs/                      # TLS certificate files
├── chroma_db/                  # Vector store (auto-generated)
├── audit_log.json              # Security event log (auto-generated)
├── query_log.json              # Query history (auto-generated)
├── ingestion_state.json        # File hash tracking (auto-generated)
├── users.json                  # User accounts (bcrypt hashes)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
│
└── futureworks/                # Implementation guides
    ├── STEP1_BCRYPT_AUTH.md
    ├── STEP2_SESSION_TIMEOUT.md
    ├── STEP3_ENV_AND_GITIGNORE.md
    ├── STEP4_AUDIT_AND_RATE_LIMITING.md
    ├── STEP5_HTTPS_BEGINNERS_GUIDE.md
    ├── STEP6_LOCAL_TESTING_CHECKLIST.md
    └── TEST_QA_SHEET.md
```

---

## Quick Start

**Prerequisites:** Python 3.10+, Google AI Studio API key ([get one free](https://aistudio.google.com))

```bash
# 1. Clone
git clone <repo-url>
cd ops-copilot_gemini

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# 5. Generate HTTPS certificate (local dev)
mkdir -p certs
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/key.pem -out certs/cert.pem \
  -days 365 -nodes -subj "/CN=localhost"

# 6. Ingest documents
python ingest.py

# 7. Start the app  (ALWAYS use the venv's streamlit)
streamlit run app.py
```

Open **`https://localhost:8501`** — accept the self-signed certificate warning in the browser.

---

## Configuration

```bash
# .env  (create this file, never commit it)
GOOGLE_API_KEY=your_google_ai_studio_key

# Confluence integration (optional)
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your@email.com
CONFLUENCE_API_TOKEN=your_token
CONFLUENCE_SPACE_KEY=SRE
```

**Tuning options in `config.py`:**

| Setting | Default | When to change |
|---|---|---|
| `CHUNK_SIZE` | 1000 | Increase if answers are cut off |
| `CHUNK_OVERLAP` | 200 | Increase if context is fragmented |
| `TOP_K_RESULTS` | 5 | Increase if sources are missing |
| `LLM_MODEL` | gemini-flash-latest | Change for different Gemini model |

---

## Document Ingestion

**Add your documents:**
```
data/markdown/customerX_runbook.md        → tagged CustomerX
data/markdown/customerY_architecture.md   → tagged CustomerY
data/yaml/customerz-deployment.yaml       → tagged General
data/markdown/general_sre_procedures.md   → tagged General
```

Files containing `customerx` in the name → tagged `CustomerX`.
Files containing `customery` → tagged `CustomerY`. Others → `General`.

**Run ingestion:**
```bash
python ingest.py              # incremental (only changed files)
python ingest.py --clear      # wipe and rebuild from scratch
```

Or use the **Ingestion Log** page → **Re-ingest all files** button.

**After ingestion, the sidebar shows the total chunk count.** A healthy knowledge base has 100+ chunks for meaningful Q&A coverage.

---

## Security Features

### bcrypt vs SHA-256

```
Attack scenario: attacker gets users.json — can they crack passwords?

SHA-256 (old):  hash takes 0.001ms  → attacker tries 1,000,000 passwords/second
bcrypt (new):   hash takes ~100ms   → attacker tries ~10 passwords/second
                                      10,000,000x slower to brute-force
```

### Audit Log — reading it

```bash
python3 -c "
import json
data = json.load(open('audit_log.json'))
for e in data['events'][-20:]:
    print(e['timestamp'][:19], '|', e['event_type'], '|', e['username'])
"
```

### Rate Limit — testing it

**Query limit:** Send more than 10 questions within 60 seconds — the 11th shows:
> ⏱️ Query rate limit: you have sent 10 queries in the last minute.

**Login lockout:** Enter wrong password 5 times for the same user — the 6th shows:
> 🔒 Too many failed login attempts. Please wait 1 hour.

---

## Pages and Dashboards

| Page | URL path | Purpose |
|---|---|---|
| Chat | `/` | Ask questions, get streaming answers with sources |
| Evaluation Dashboard | `/Evaluation_Dashboard` | RAGAS quality metrics |
| Ingestion Log | `/Ingestion_Log` | Document status, re-ingest controls |
| Usage Dashboard | `/Usage_Dashboard` | Query volume, latency, user analytics |
| Admin Panel | `/Admin_Panel` | Create and delete user accounts |

---

## UI Walkthrough

Visual walkthrough of every screen in the application.

---

### Login Page

The first screen every user sees. Centred login form with username and password fields.
Session is initialised immediately on successful login — the inactivity timer starts from this moment.

```
┌──────────────────────────────────────────────────────────────────────┐
│  🔒 https://localhost:8501                                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                                                                      │
│                         🔍 SRE Ops Copilot                          │
│                         Sign in to continue                          │
│                    ──────────────────────────────                    │
│                                                                      │
│                    Username                                          │
│                    ┌──────────────────────────┐                      │
│                    │ admin                    │                      │
│                    └──────────────────────────┘                      │
│                                                                      │
│                    Password                                          │
│                    ┌──────────────────────────┐                      │
│                    │ ••••••••••••••           │                      │
│                    └──────────────────────────┘                      │
│                                                                      │
│                    ┌──────────────────────────┐                      │
│                    │         Sign in          │  ← primary button    │
│                    └──────────────────────────┘                      │
│                                                                      │
│                                                                      │
│   Wrong password → ⚠ Incorrect username or password.                │
│   5 fails        → 🔒 Too many failed login attempts. Wait 1 hour.  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Main Chat Interface

The primary page. Left sidebar shows session info, quick-start buttons, and knowledge chunk count.
Right area is the full-width chat. Answers stream in word-by-word as Gemini generates them.

```
┌────────────────────┬─────────────────────────────────────────────────┐
│  SRE Ops Copilot   │   SRE Knowledge Base                            │
│  AI-powered        │   Searching as: admin  |  Access: All Customers │
│  knowledge base    ├─────────────────────────────────────────────────┤
│                    │                                                  │
│  ✓ Admin           │   ℹ Ask me anything about your customer         │
│  [ Sign out ]      │     deployments. I will search the knowledge    │
│                    │     base and cite my sources.                    │
│  ▶ Session Info    │                                                  │
│                    │   ┌─────────────────────────────────────────┐   │
│  ─────────────     │   │ 👤  What version is CustomerX running?  │   │
│                    │   └─────────────────────────────────────────┘   │
│  🔓 Full Access    │                                                  │
│     Mode           │   ┌─────────────────────────────────────────┐   │
│     Search across  │   │ 🤖  CustomerX is running WSO2 API       │   │
│     all customer   │   │     Manager version **4.2.1**, deployed  │   │
│     documents      │   │     on Azure Kubernetes Service (AKS)   │   │
│                    │   │     in the East US 2 region.            │   │
│  ─────────────     │   │     The cluster uses Standard_D4s_v3   │   │
│                    │   │     nodes with autoscaling min 2,       │   │
│  Total chunks      │   │     max 8...                   ▌        │   │
│  ┌────────────┐    │   │                                          │   │
│  │     45     │    │   │  Sources: [customerX_architecture.md]   │   │
│  └────────────┘    │   │           [customerX_runbook.md]        │   │
│                    │   │  ▼ View 5 source(s)                     │   │
│  Try asking:       │   └─────────────────────────────────────────┘   │
│  ┌──────────────┐  │                                                  │
│  │What version  │  │   ┌─────────────────────────────────────────────┐│
│  │is CustomerX? │  │   │ Ask about any customer deployment...    ▶   ││
│  └──────────────┘  │   └─────────────────────────────────────────────┘│
│  ┌──────────────┐  │                                                  │
│  │What AKS node │  │   SRE Ops Copilot · Powered by Gemini ·         │
│  │pool does     │  │   Answers grounded in retrieved docs only.       │
│  │CustomerX use?│  └──────────────────────────────────────────────────┘
│  └──────────────┘
│  ┌──────────────┐
│  │Who are the   │  Key features visible here:
│  │escalation    │  • Sidebar shows live session countdown
│  │contacts?     │  • Source chips appear under every answer
│  └──────────────┘  • ▼ Expander shows file path + similarity %
│  ┌──────────────┐  • Suggested question buttons on the left
│  │Any known     │  • Rate limit error shown here if exceeded
│  │issues for    │
│  │CustomerX?    │
│  └──────────────┘
│
│  [ Clear conversation ]
└────────────────────┘
```

**Source citation expander** — clicking "View 5 source(s)" reveals:

```
  ▼ View 5 source(s)
  ┌─────────────────────────────────────────┬──────────┬──────────┐
  │ Source                                  │ Customer │  Match   │
  ├─────────────────────────────────────────┼──────────┼──────────┤
  │ data/markdown/customerX_architecture.md │CustomerX │   87%    │
  │ data/markdown/customerX_runbook.md      │CustomerX │   82%    │
  │ data/yaml/customerx-deployment.yaml     │CustomerX │   74%    │
  │ data/markdown/general_sre_procedures.md │ General  │   61%    │
  │ data/markdown/customerX_architecture.md │CustomerX │   58%    │
  └─────────────────────────────────────────┴──────────┴──────────┘
```

**Session expiry screen** — shown when inactive for 60 minutes:

```
  ⚠ Your session has expired due to inactivity (60 minutes).
     Please log in again to continue.

     ──────────────────────────────────────────

            [ 🔒 Click here to log in again ]
```

---

### Usage Dashboard  (`/Usage_Dashboard`)

Query analytics for the admin team. Shows who is using the system, how fast it responds, and where failures happen.

```
┌──────────────────────────────────────────────────────────────────────┐
│  📈 Usage Dashboard                                                  │
│  Query analytics and system usage                                    │
├────────────────┬────────────────┬────────────────┬───────────────────┤
│  Total queries │  Unique users  │  Avg latency   │   Success rate    │
│                │                │                │                   │
│      47        │       4        │   1847 ms      │      94.0%        │
│                │                │                │                   │
├────────────────┴────────────────┴────────────────┴───────────────────┤
│                                                                      │
│  Queries per day                                                     │
│                                                                      │
│  15 ┤                         ██                                     │
│  12 ┤                    ██   ██                                     │
│   9 ┤              ██    ██   ██                                     │
│   6 ┤         ██   ██    ██   ██                                     │
│   3 ┤    ██   ██   ██    ██   ██   ██                                │
│   0 └────────────────────────────────────────────                    │
│      May-09 May-10 May-11 May-12 May-13 May-14                      │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  Response Time Distribution (ms)                                     │
│                                                                      │
│  3000 ┤ █                                                            │
│  2500 ┤ ██    █                                                      │
│  2000 ┤ ██  █ ██  █   █  ██  █                                      │
│  1500 ┤ ██  █ ██  ██  ██ ██  █                                      │
│  1000 ┤ ██  █ ██  ██  ██ ██  █                                      │
│       └────────────────────────────                                  │
│        ← last 50 queries →                                           │
│                                                                      │
├───────────────────────────┬──────────────────────────────────────────┤
│  Queries by user          │  Most retrieved sources                  │
│                           │                                          │
│  User      │  Queries     │  Source              │  Times retrieved  │
│  ──────────┼──────────    │  ────────────────────┼────────────────   │
│  admin     │    28        │  customerX_arch.md   │       14          │
│  alice     │    11        │  customerX_runbook.md│       11          │
│  samith    │     6        │  customerZ_arch.md   │        9          │
│  chalaka   │     2        │  customerY_arch.md   │        7          │
│                           │  general_sre_proc.md │        5          │
│                           │                                          │
├───────────────────────────┴──────────────────────────────────────────┤
│  Recent queries (last 20)                                            │
│                                                                      │
│  Timestamp           │ User   │ Question              │ ms  │  OK   │
│  ────────────────────┼────────┼───────────────────────┼─────┼────── │
│  2026-05-13 16:23:11 │ admin  │ What version is Cus.. │1823 │  ✅   │
│  2026-05-13 16:21:44 │ alice  │ Who is the escalatio..│2104 │  ✅   │
│  2026-05-13 16:19:02 │ samith │ Known issues CustomerZ│1756 │  ✅   │
│  2026-05-13 16:16:55 │ admin  │ CustomerX SLA uptime  │1932 │  ✅   │
│  ...                                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Evaluation Dashboard  (`/Evaluation_Dashboard`)

Runs automated quality checks on the RAG pipeline using the RAGAS framework.
Measures whether answers are accurate, relevant, and grounded in the retrieved documents.

```
┌──────────────────────────────────────────────────────────────────────┐
│  📊 RAG Evaluation Dashboard                                         │
│  Answer quality metrics powered by RAGAS                            │
├──────────────────┬───────────────────────┬───────────────────────────┤
│  Faithfulness    │   Answer Relevancy    │   Context Precision       │
│                  │                       │                           │
│  How grounded    │  How relevant is      │  How precise are the      │
│  is the answer   │  the answer to the    │  retrieved chunks to      │
│  in the docs?    │  question?            │  the question?            │
│                  │                       │                           │
│     0.91 / 1.0   │      0.87 / 1.0       │      0.83 / 1.0          │
│  ██████████░     │   █████████░░         │   ████████░░░            │
│                  │                       │                           │
├──────────────────┴───────────────────────┴───────────────────────────┤
│                                                                      │
│  Per-question scores                                                 │
│                                                                      │
│  #  │ Question                    │ Faith │ Relev │ Prec  │ Overall │
│  ───┼─────────────────────────────┼───────┼───────┼───────┼──────── │
│  1  │ What version is CustomerX?  │ 1.00  │ 0.95  │ 0.90  │  0.95  │
│  2  │ Who is escalation contact?  │ 1.00  │ 0.92  │ 0.88  │  0.93  │
│  3  │ What database CustomerZ?    │ 0.90  │ 0.88  │ 0.85  │  0.88  │
│  4  │ CustomerY known issues?     │ 0.85  │ 0.82  │ 0.80  │  0.82  │
│  5  │ CustomerX maintenance win?  │ 0.88  │ 0.84  │ 0.79  │  0.84  │
│  ...│                             │       │       │       │        │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  [ ▶ Re-run Evaluation ]                                             │
│                                                                      │
│  Last evaluated: 2026-05-13 15:44  |  Test set: 10 questions         │
└──────────────────────────────────────────────────────────────────────┘

  What each metric means:
  • Faithfulness    — Is every claim in the answer supported by the retrieved docs?
                      1.0 = no hallucination.  0.0 = completely made up.
  • Answer Relevancy — Does the answer actually address the question asked?
  • Context Precision — Are the top retrieved chunks genuinely relevant,
                        or is the retrieval polluted with unrelated content?
```

---

### Ingestion Log  (`/Ingestion_Log`)

Shows every document the system knows about, when they were last processed, and lets you trigger re-ingestion from the UI.

```
┌──────────────────────────────────────────────────────────────────────┐
│  📥 Ingestion Log                                                    │
│  Document ingestion status and history                               │
├───────────────────────────────┬──────────────────────────────────────┤
│  Last ingestion               │  Total files tracked                 │
│  2026-05-13  13:31            │            15                        │
├───────────────────────────────┴──────────────────────────────────────┤
│                                                                      │
│  Tracked Files                                                       │
│                                                                      │
│  #  │ File                         │ Path           │ Hash    │Exists│
│  ───┼──────────────────────────────┼────────────────┼─────────┼───── │
│  0  │ customerX_architecture.md    │ data/markdown  │ 856c4b52│  ✅  │
│  1  │ customerX_runbook.md         │ data/markdown  │ a3f1d229│  ✅  │
│  2  │ customerY_architecture.md    │ data/markdown  │ c7e90b11│  ✅  │
│  3  │ customerY_runbook.md         │ data/markdown  │ 4d82ef30│  ✅  │
│  4  │ customerZ_architecture.md    │ data/markdown  │ 9b1ca567│  ✅  │
│  5  │ customerZ_runbook.md         │ data/markdown  │ 2a7fd843│  ✅  │
│  6  │ general_sre_procedures.md    │ data/markdown  │ f04bc910│  ✅  │
│  7  │ customerx-deployment.yaml    │ data/yaml      │ d8d0a7df│  ✅  │
│  8  │ customerx-hpa.yaml           │ data/yaml      │ 11e3bc02│  ✅  │
│  ...│                              │                │         │      │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  Manual Actions                                                      │
│                                                                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐   │
│  │  🔄 Re-ingest all files  │    │  🗑 Clear database and        │   │
│  │  (adds new/changed docs) │    │    re-ingest (full rebuild)   │   │
│  └──────────────────────────┘    └──────────────────────────────┘   │
│                                                                      │
│  After clicking → spinner shows progress output from ingest.py:      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Loading embedding model...                                  │   │
│  │  Loaded 7 markdown files                                     │   │
│  │  Split 7 documents into 43 chunks                            │   │
│  │  Converting 43 chunks to vectors...  ████████░░  80%         │   │
│  │  Stored 43 chunks in ChromaDB                               │   │
│  │  ✅ Ingestion complete! Refresh page to see updates.         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

  Exists column:
  ✅ = file still exists on disk at that path
  ❌ = file was deleted or moved — re-ingest to remove from DB
```

---

### Admin Panel  (`/Admin_Panel`)

User management for administrators. Create accounts with bcrypt-hashed passwords automatically.
Delete users instantly. Non-admin users cannot access this page (auth_guard blocks them).

```
┌──────────────────────────────────────────────────────────────────────┐
│  👤 Admin Panel                                                      │
│  User management                                   [ admin only ]    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Current Users                                                       │
│                                                                      │
│  Username   │  Display Name      │  Role    │  Action               │
│  ───────────┼────────────────────┼──────────┼────────────────────── │
│  admin      │  Admin             │  admin   │  (cannot delete self) │
│  alice      │  Alice (SRE)       │  user    │  [ 🗑 Delete ]        │
│  samith     │  Samith (Intern)   │  user    │  [ 🗑 Delete ]        │
│  chalaka    │  Chalaka (Lead)    │  user    │  [ 🗑 Delete ]        │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Create New User                                                     │
│                                                                      │
│  Username        [ new_user              ]                           │
│  Display Name    [ New User (Role)       ]                           │
│  Password        [ ••••••••••••••        ]                           │
│  Confirm Pwd     [ ••••••••••••••        ]                           │
│                                                                      │
│  ┌──────────────────────┐                                            │
│  │   Create User        │  ← password is bcrypt-hashed on save      │
│  └──────────────────────┘                                            │
│                                                                      │
│  ✅ User 'new_user' created successfully.                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

  Security notes:
  • Password is never stored in plaintext — bcrypt hash written to users.json
  • Admin can only be created manually — no self-registration
  • Audit log records every USER_CREATED and USER_DELETED event
```

---

### Rate Limit Error  (shown in chat when limit exceeded)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  👤  What is the latest known issue for CustomerZ?            │
  └──────────────────────────────────────────────────────────────┘

  🚫 ⏱️ Query rate limit: you have sent 10 queries in the last
        minute. Please wait 60 seconds before asking another
        question.

  💡 Rate limits ensure fair API usage across the team.
```

---

### Session Timeout Warning  (shown on any page after 60 min idle)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  ⚠ Your session has expired due to inactivity (60 minutes).  │
  │    Please log in again to continue.                          │
  │                                                              │
  │  ──────────────────────────────────────────────────────      │
  │                                                              │
  │          [ 🔒  Click here to log in again ]                  │
  └──────────────────────────────────────────────────────────────┘
```

---

## Testing

A 37-question manual test sheet is at `futureworks/TEST_QA_SHEET.md` covering:
- Version questions (which customer runs which version)
- Infrastructure details (node types, regions, databases)
- Known issues and workarounds
- Escalation contacts
- SLA and maintenance windows
- kubectl procedures
- Cross-customer comparisons

**Scoring:**

| Score | Meaning |
|---|---|
| 34–37 correct | Excellent — RAG working well |
| 28–33 correct | Good — minor retrieval gaps |
| Below 28 | Check ingestion and chunk settings |

---

## Deployment

### Local (development)
```bash
source venv/bin/activate
streamlit run app.py
# https://localhost:8501
```

### Docker
```bash
docker-compose up --build
```

### Production (cloud VM)
See `futureworks/STEP5_HTTPS_BEGINNERS_GUIDE.md` for a full beginner-friendly guide to:
- Setting up Nginx as a reverse proxy
- Getting a free Let's Encrypt certificate with Certbot
- Running as a systemd service that survives reboots

---

## What I Learned

This was my first internship project. Key concepts I encountered for the first time:

| Concept | What I learned |
|---|---|
| RAG architecture | How to combine vector search with LLM generation to ground answers in real data instead of hallucinating |
| Vector databases | How ChromaDB stores and retrieves embeddings using cosine similarity and HNSW indexing |
| Security hardening | Why bcrypt is fundamentally different from SHA-256; what session timeouts and rate limiting actually protect against |
| HTTPS / TLS | How certificates work, what a CA is, why self-signed certs trigger browser warnings |
| Streamlit internals | Session state, streaming generators, multi-page auth, Python module caching behaviour |
| Python venv isolation | Why the wrong venv causes subtle, hard-to-diagnose errors |
| Atomic file writes | Why `write to temp → rename` prevents corrupt files on crash |
| Docker containerisation | How to package an app with all its runtime dependencies reproducibly |

---

*First internship project — Enterprise IT Company SRE Team*
