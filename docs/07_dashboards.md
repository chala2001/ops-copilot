# 07 — Dashboards: Every Page Explained

> What each page shows, who can access it, and how the data flows.

---

## How Multi-Page Navigation Works

Streamlit automatically creates a sidebar navigation from files in the `pages/` folder. The numbers in filenames control the order:

```
app.py                        → "SRE Ops Copilot" (main chat, page 1)
pages/2_Evaluation_Dashboard  → "Evaluation Dashboard"
pages/3_Ingestion_Log         → "Ingestion Log"
pages/4_Usage_Dashboard       → "Usage Dashboard"
pages/5_Admin_Panel           → "Admin Panel"
```

Every page calls `require_authentication()` at the top. If you're not logged in and try to navigate directly to `/Evaluation_Dashboard`, you'll see "Access Denied" and a prompt to log in via the main page first.

---

## Page 1: SRE Ops Copilot (app.py) — Main Chat

**Who can access:** All authenticated users  
**File:** [app.py](../app.py)

### What It Shows

```
┌─────────────────────────────────────────────────────────────────┐
│ SIDEBAR                    │ MAIN AREA                          │
│                            │                                     │
│ SRE Ops Copilot            │ SRE Knowledge Base                  │
│ AI-powered knowledge base  │ Searching as: alice | Access: All  │
│                            │                                     │
│ ✓ Alice (Senior SRE)       │ [Welcome message if no history]    │
│ [Sign out]                 │                                     │
│                            │ ┌─────────────────────────────────┐ │
│ Session Info               │ │ user: What version is CustomerX?│ │
│ ⏱️ Session: 15 min          │ │                                 │ │
│ 🔒 Auto-logout: 45 min     │ │ assistant: Based on the          │ │
│                            │ │ runbook, CustomerX is running   │ │
│ 🔓 Full Access Mode        │ │ WSO2 API Manager 4.2.0...      │ │
│                            │ │ Sources: customerX_runbook.md   │ │
│ Try asking:                │ └─────────────────────────────────┘ │
│ [What version is CustX?]   │                                     │
│ [What AKS node pool...]    │ [Ask about any customer deployment]│
│ [Escalation contacts...]   │                                     │
│ [Known issues...]          │                                     │
│                            │                                     │
│ [Clear conversation]       │                                     │
│                            │                                     │
│ Total knowledge chunks: 87 │                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

**Suggested questions:** Sidebar buttons inject a pre-written question into the chat input. Clicking "What version is CustomerX running?" sets `st.session_state.prefilled_question`, which app.py checks and uses as the prompt on the next rerun.

**Source citations:** After each answer, sources appear as small blue "chips" showing the document filename. Clicking "View N source(s)" expands a table showing full path, customer, and similarity percentage.

**Knowledge chunk count:** `collection.count()` shows how many chunks are in ChromaDB — useful to confirm ingestion ran.

**Clear conversation:** Resets `st.session_state.messages = []` and reruns.

---

## Page 2: Evaluation Dashboard (2_Evaluation_Dashboard.py)

**Who can access:** All authenticated users  
**File:** [pages/2_Evaluation_Dashboard.py](../pages/2_Evaluation_Dashboard.py)  
**Data source:** `evaluation_results.json` (created by `python evaluate.py`)

### What It Shows

```
📊 RAG Quality Dashboard
Last evaluated: 2026-05-10 14:23 | 5 questions | Model: gemini-flash-latest

┌──────────────────────┐  ┌──────────────────────┐
│ Faithfulness         │  │ Answer Relevancy      │
│ 92.0%               │  │ 88.0%                │
│ ↑ Above target      │  │ ↑ Above target        │
└──────────────────────┘  └──────────────────────┘

Per-Question Scores:
┌────────────────────────────────────────┬─────────────┬────────────────┐
│ Question                               │ Faithfulness│ Answer Rel.   │
├────────────────────────────────────────┼─────────────┼────────────────┤
│ What version is CustomerX running?     │ 95%  (green)│ 91%  (green)  │
│ What AKS node pool does CustomerX use? │ 88%  (green)│ 84%  (green)  │
│ Escalation contacts for CustomerX?     │ 72%  (orange│ 68%  (orange) │
│ ...                                    │             │                │
└────────────────────────────────────────┴─────────────┴────────────────┘

[Re-run evaluation now] button
```

### Color Coding

| Score | Color | Meaning |
|-------|-------|---------|
| > 75% | Green | Good |
| 50–75% | Orange | Needs attention |
| < 50% | Red | Problem — check your documents |

### The Re-Run Button

Clicking "Re-run evaluation now" launches a subprocess:
```python
result = subprocess.run(
    [sys.executable, 'evaluate.py'],
    timeout=300,
    cwd=os.getcwd()
)
```

After it finishes (2-3 minutes), the page reruns and shows fresh scores.

### What to Do If Scores Are Low

**Low Faithfulness:** Gemini is adding information not in your documents.
- Check if `TOP_K_RESULTS` is too low (increase to get more context)
- Improve your system prompt to be stricter about only using context

**Low Answer Relevancy:** Answers are going off-topic.
- Your chunking may be splitting important context across chunks
- Try reducing `CHUNK_SIZE` for better granularity

---

## Page 3: Ingestion Log (3_Ingestion_Log.py)

**Who can access:** All authenticated users  
**File:** [pages/3_Ingestion_Log.py](../pages/3_Ingestion_Log.py)  
**Data source:** `ingestion_state.json` (created by `python ingest.py`)

### What It Shows

```
📥 Ingestion Log
Document ingestion status and history

┌──────────────────────────────┐  ┌───────────────────────┐
│ Last ingestion               │  │ Total files tracked   │
│ 2026-05-10 09:15             │  │ 7                     │
└──────────────────────────────┘  └───────────────────────┘

Tracked Files:
┌───────────────────────────┬──────────────────┬──────────┬────────┐
│ File                      │ Path             │ Hash     │ Exists │
├───────────────────────────┼──────────────────┼──────────┼────────┤
│ customerX_runbook.md      │ data/markdown    │ a1b2c3d4 │ ✅    │
│ customerX_architecture.md │ data/markdown    │ e5f6g7h8 │ ✅    │
│ customerY_runbook.md      │ data/markdown    │ i9j0k1l2 │ ✅    │
└───────────────────────────┴──────────────────┴──────────┴────────┘

Manual Actions:
[🔄 Re-ingest all files]    [🗑️ Clear database and re-ingest]
```

### The Buttons

**Re-ingest all files:** Runs `python ingest.py` — adds/updates documents without clearing existing chunks.

**Clear database and re-ingest:** Runs `python ingest.py --clear` — deletes all chunks from ChromaDB first, then re-ingests. Use when you've modified existing documents.

### The File Hash Column

The "Hash (first 8)" column shows the first 8 characters of the MD5 hash computed when the file was last ingested. If you edit a file after ingestion, the current file hash would differ from the stored one — which is your signal to re-ingest.

The "Exists" column shows ✅ if the file is still on disk, ❌ if it's been deleted. A missing file means those chunks are still in ChromaDB but the source document is gone — you should clear and re-ingest.

---

## Page 4: Usage Dashboard (4_Usage_Dashboard.py)

**Who can access:** All authenticated users  
**File:** [pages/4_Usage_Dashboard.py](../pages/4_Usage_Dashboard.py)  
**Data source:** `query_log.json` (auto-populated on every query)

### What It Shows

```
📈 Usage Dashboard
Query analytics and system usage

┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Total queries│ │ Unique users │ │ Avg latency  │ │ Success rate │
│ 147          │ │ 4            │ │ 1,250 ms     │ │ 98.6%        │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘

Queries per day:
  [Bar chart showing daily query counts]

Response Time Distribution (ms):
  [Bar chart of last 50 query latencies]

Queries by user:          Most retrieved sources:
  alice    89              customerX_runbook.md      45
  chalaka  32              customerX_architecture.md 28
  carol    26              general_sre_procedures.md 22

Recent queries (last 20):
  [Table: timestamp | username | question | latency_ms | success]

⚠️ Failed queries (2):
  [Table: timestamp | username | question | error]
```

### How to Use This Data

**High average latency (>3000ms):** Gemini is slow. May be API rate limits or slow network. Check your internet connection or try a different Gemini model.

**Low success rate:** Queries are failing. Check the "Failed queries" table to see the error messages. Common causes: Gemini API key expired, rate limit exceeded at Gemini level.

**One user dominates queries:** They may be hitting rate limits. Consider raising `MAX_QUERIES_PER_HOUR` for power users.

**Same document always top-retrieved:** Your knowledge base may be too small. Add more documents to spread the retrieval load.

---

## Page 5: Admin Panel (5_Admin_Panel.py)

**Who can access:** Only users with `role: admin`  
**File:** [pages/5_Admin_Panel.py](../pages/5_Admin_Panel.py)  
**Security:** Role check immediately after `require_authentication()`

### What It Shows

```
⚙️ Admin Panel
User management and system administration

Current Users:
┌──────────┬─────────────────────┬──────────────┬──────────┐
│ Username │ Display Name        │ Role         │ Access   │
├──────────┼─────────────────────┼──────────────┼──────────┤
│ alice    │ Alice (Senior SRE)  │ senior_sre   │ ALL      │
│ carol    │ Carol (SRE)         │ sre          │ ALL      │
│ admin    │ Admin               │ admin        │ ALL      │
│ chalaka  │ Chalaka             │ sre          │ ALL      │
└──────────┴─────────────────────┴──────────────┴──────────┘
Total Users: 6

────────────────────────────────────────

Add New User:
  Username: [          ]   Password Requirements:
  Password: [          ]   • Minimum 8 characters
  Confirm:  [          ]   • Mix of uppercase/lowercase/numbers
  Name:     [          ]   • Passwords hashed with bcrypt (cost 12)
  Role: [sre ▼]
  [Add User]

────────────────────────────────────────

Remove User:
  [alice ▼]  ☐ I understand this is permanent
  [Delete User]    (Cannot delete your own account)

────────────────────────────────────────

System Information:
  Total Users: 6    Total Queries: 147    Documents Ingested: 7
```

### Security: You Cannot Delete Yourself

```python
deletable_users = [u for u in users.keys() if u != user_info['username']]
```

The admin logged in cannot delete their own account — this prevents accidentally locking everyone out.

### Password Hashing on Create

When the admin submits the "Add User" form, the code calls `auth.create_user()` which calls `hash_password()` — the plain-text password is hashed with bcrypt before it ever touches `users.json`. The admin cannot see the password in the stored data.

### Role Assignment

| Role | What It Means in Practice |
|------|--------------------------|
| `sre` | Regular team member — chat and dashboards |
| `senior_sre` | Same as SRE (role reserved for future expanded permissions) |
| `admin` | Everything + Admin Panel access |
