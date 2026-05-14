# SRE Ops Copilot — Complete Learning Guide

> **This is your starting point.** Read the docs in order for a full presentation-ready understanding of every part of this system.

---

## What Is This System?

**SRE Ops Copilot** is an AI-powered knowledge assistant built for Site Reliability Engineering teams. Instead of digging through folders of documents, runbooks, or Confluence pages to answer a customer question, an SRE can just type: *"What version is CustomerX running?"* and get an instant, document-backed answer.

It is a **RAG system** — Retrieval-Augmented Generation. That means it searches your own internal documents and uses Google's Gemini AI to compose a precise answer from what it finds.

---

## Table of Contents — Read in This Order

| # | File | What You Will Learn |
|---|------|---------------------|
| 1 | [01_architecture.md](01_architecture.md) | The big picture — how all parts connect |
| 2 | [02_streamlit_explained.md](02_streamlit_explained.md) | What Streamlit is and how the app runs as a server |
| 3 | [03_rag_pipeline.md](03_rag_pipeline.md) | How RAG works — from your documents to an AI answer |
| 4 | [04_authentication.md](04_authentication.md) | Login, passwords, bcrypt — full deep dive |
| 5 | [05_security.md](05_security.md) | Rate limits, sessions, audit logs, HTTPS |
| 6 | [06_code_files.md](06_code_files.md) | Every Python file explained line by line |
| 7 | [07_dashboards.md](07_dashboards.md) | Each dashboard page and what it shows |
| 8 | [08_evaluation.md](08_evaluation.md) | How we measure if the AI is any good |
| 9 | [09_commands.md](09_commands.md) | Every command to run the system |

---

## Quick System Facts

| Property | Value |
|----------|-------|
| UI Framework | Streamlit (Python web framework) |
| AI Model | Google Gemini Flash (via API) |
| Vector Database | ChromaDB (runs locally on disk) |
| Embedding Model | all-MiniLM-L6-v2 (free, runs locally) |
| Password Hashing | bcrypt (cost factor 12) |
| Document Types | Markdown, PDF, YAML |
| Transport Security | HTTPS with TLS certificates |

---

## The 4 Things This System Does

1. **Ingests documents** — reads your runbooks, architecture docs, and stores them as searchable vectors in ChromaDB
2. **Answers questions** — takes a user's question, searches the vector database, sends context to Gemini, streams the answer back
3. **Secures access** — enforces login, session timeouts, rate limits, and audit logging
4. **Shows analytics** — dashboards for query history, usage stats, AI quality scores, and admin user management
