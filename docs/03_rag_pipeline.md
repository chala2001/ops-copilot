# 03 — The RAG Pipeline: From Documents to AI Answers

> RAG stands for Retrieval-Augmented Generation. This document explains every step — from ingesting a runbook file to streaming an answer to the user.

---

## Why RAG? The Problem It Solves

**The problem with plain AI:**
If you just ask Gemini "What version is CustomerX running?", it will say "I don't know" or make something up — because this information is not in its training data. It's your private internal document.

**The solution:**
Before asking Gemini for an answer, we search our own documents and hand Gemini the relevant paragraphs as "context". Gemini then writes an answer based only on what we gave it.

Think of it like an open-book exam:
- Without RAG: Gemini has to answer from memory (it doesn't have your docs)
- With RAG: Gemini gets to read the relevant pages before answering

---

## The Two Phases in Detail

---

## Phase 1: Ingestion (ingest.py)

This runs once before anyone uses the app. Run it with: `python ingest.py`

### Step 1.1 — Load Documents

The ingestion script reads files from three folders:

```
data/markdown/   ← .md files (runbooks, architecture docs)
data/pdf/        ← .pdf files
data/yaml/       ← Kubernetes YAML configuration files
```

Each file is loaded and becomes a LangChain "Document" object. A Document object has:
- `page_content` — the text of the document
- `metadata` — info about the document (file path, customer name, doc type)

### Step 1.2 — Add Customer Metadata

After loading, the code reads each file's name to figure out which customer it belongs to:

```python
if 'customerx' in filename:
    doc.metadata['customer'] = 'CustomerX'
elif 'customery' in filename:
    doc.metadata['customer'] = 'CustomerY'
else:
    doc.metadata['customer'] = 'General'
```

This metadata is stored with each chunk in ChromaDB and is used later to filter search results by customer.

### Step 1.3 — Split Into Chunks

A document like `customerX_runbook.md` might be 5,000 words. Sending the entire document to an embedding model or AI is wasteful and less accurate. Instead, we split it into smaller pieces:

```
Config:
  CHUNK_SIZE    = 1000 characters  (~200-250 words)
  CHUNK_OVERLAP = 200 characters   (overlap prevents cutting mid-thought)
```

**Why overlap?** Imagine a sentence that starts at character 998 of a document. Without overlap, it would be split across two chunks and neither chunk contains the full sentence. With 200-character overlap, the end of chunk 1 and the start of chunk 2 share 200 characters, so nothing is lost.

```
Document (5000 chars):
[chunk 1: 0→1000]
          [chunk 2: 800→1800]   ← 200 char overlap
                    [chunk 3: 1600→2600]
                              ...
```

### Step 1.4 — Convert Chunks to Vectors (Embeddings)

This is the core of the system. We use a model called `all-MiniLM-L6-v2` to convert every chunk of text into a list of 384 numbers called a **vector** or **embedding**.

**Analogy:** Think of the embedding as giving each text chunk GPS coordinates. Similar texts (about the same topic) get coordinates that are close together. Unrelated texts get coordinates that are far apart.

```
"CustomerX runs WSO2 API Manager 4.2.0"
  → [0.12, -0.34, 0.89, 0.01, -0.45, ... ] (384 numbers)

"CustomerY has a known issue with pods"
  → [0.08, 0.67, -0.23, 0.91, 0.12, ... ] (384 numbers)
```

The model runs entirely on your machine — no internet, no API cost. It runs once during ingestion and is loaded again during query time.

### Step 1.5 — Store in ChromaDB

ChromaDB is a vector database. Think of it as a special database that can efficiently store and search through millions of these 384-number vectors.

```python
collection.upsert(
    ids=['customerX_runbook_chunk_0', 'customerX_runbook_chunk_1', ...],
    documents=['text of chunk...', 'text of chunk...', ...],
    embeddings=[[0.12, -0.34, ...], [0.08, 0.67, ...], ...],
    metadatas=[{'customer': 'CustomerX', 'source': '...', 'doc_type': 'markdown'}, ...]
)
```

ChromaDB saves everything to `./chroma_db/` on disk. This persists across server restarts — you don't need to re-ingest every time the app restarts.

---

## Phase 2: Query Answering (rag.py)

This happens every time a user asks a question. The function `ask_stream()` in rag.py orchestrates all of this.

### Step 2.1 — Embed the Question

The user's question is converted to a vector using the same embedding model:

```python
question_embedding = embedder.encode(question).tolist()
# question = "What version is CustomerX running?"
# → [0.11, -0.31, 0.87, 0.03, ...] (384 numbers)
```

This is the "GPS coordinate" of the user's question.

### Step 2.2 — Search ChromaDB

ChromaDB finds the 5 chunks whose vectors are closest to the question vector:

```python
results = collection.query(
    query_embeddings=[question_embedding],
    n_results=5,                                   # return top 5 chunks
    where={'customer': {'$in': ['ALL']}},          # filter by customer (optional)
    include=['documents', 'metadatas', 'distances']
)
```

"Closest" means mathematically most similar in 384-dimensional space. This is called **cosine similarity**. Documents about CustomerX versions will be close to a question about CustomerX versions, because both texts use the same concepts and terminology.

The `distances` value tells us how similar each result is. We convert it to a percentage:
```
similarity = round(1 - distance, 3)
# distance of 0.1 → similarity = 0.9 = 90% match
```

### Step 2.3 — Build the Context String

The 5 retrieved chunks are assembled into a "context" string with source labels:

```
[Source 1: data/markdown/customerX_runbook.md | Customer: CustomerX]
CustomerX is running WSO2 API Manager 4.2.0 on AKS...

---

[Source 2: data/markdown/customerX_architecture.md | Customer: CustomerX]
The production cluster uses Standard_D4s_v3 nodes...

---

[Source 3: ...]
...
```

This context will be given to Gemini in the next step.

### Step 2.4 — Build the Prompt

We combine a system prompt (instructions for Gemini) with the context and the user's question:

```
System: "You are an SRE assistant for the WSO2 operations team.
Answer ONLY from the provided context. If the answer is not in
the context, say so. Be concise and technically precise."

Context:
  [Source 1: ...] chunk text...
  [Source 2: ...] chunk text...
  ...

Question: "What version is CustomerX running?"

Answer based only on the context above:
```

The key instruction is "Answer ONLY from the provided context." This prevents Gemini from making things up or pulling in information that's not in your documents.

### Step 2.5 — Stream Gemini's Answer

We call Gemini's streaming API:

```python
response = client.models.generate_content_stream(
    model='gemini-flash-latest',
    contents=full_prompt
)

for chunk in response:     # Gemini sends tokens as they're generated
    if chunk.text:
        yield chunk.text   # each token is sent immediately to the browser
```

The user sees the answer appearing word by word, like watching someone type in real time.

### Step 2.6 — Yield Sources and Log

After all text is yielded, we yield the sources list so app.py can display the source citations:

```python
yield sources  # [{source: '...', customer: '...', similarity: 0.92}, ...]
```

Back in app.py, after streaming finishes:
- The answer and sources are saved to `st.session_state.messages` (chat history)
- `logger.log_query()` records everything to `query_log.json`

---

## Visualizing the Similarity Search

Imagine each document chunk as a point in space. When you ask a question, it's also a point. ChromaDB finds the 5 nearest points to your question point:

```
                        ● customerX_runbook chunk 1  (92% match)
                       ●  customerX_architecture chunk 3  (87% match)
                      ●   customerX_runbook chunk 5  (81% match)
                     ●    customerY_runbook chunk 2  (65% match — less relevant)
  ★ [your question] ●     general_sre_procedures chunk 8  (60% match)

                                  .
                         .
              . unrelated chunks are far away
```

---

## The Config Values That Control RAG Quality

In `config.py`:

| Setting | Value | Effect |
|---------|-------|--------|
| `CHUNK_SIZE` | 1000 chars | Bigger = more context per chunk, but less precise matching |
| `CHUNK_OVERLAP` | 200 chars | More = less information loss at boundaries |
| `TOP_K_RESULTS` | 5 | More chunks = more context for Gemini, but more tokens = more cost |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | The model that creates vectors |
| `LLM_MODEL` | gemini-flash-latest | The model that writes the answer |

---

## What Files Are in data/markdown/ Right Now?

```
customerX_architecture.md    ← CustomerX system design
customerX_runbook.md         ← CustomerX operational procedures
customerY_runbook.md         ← CustomerY operational procedures
customerZ_architecture.md    ← CustomerZ system design
customerZ_runbook.md         ← CustomerZ operational procedures
cutomerY_architecture.md     ← CustomerY system design (note: typo in filename)
general_sre_procedures.md    ← Team-wide SRE procedures
```

These are all indexed in ChromaDB. Any question about these customers will retrieve relevant chunks from these files.

---

## The ingest.py --clear Flag

```bash
python ingest.py           # add new documents (keeps existing ones)
python ingest.py --clear   # delete all chunks, then re-ingest from scratch
```

Use `--clear` when:
- You changed existing documents (not just added new ones)
- The database seems corrupt
- You want to start completely fresh

Without `--clear`, it uses `upsert` which adds-or-updates based on the chunk ID. If a chunk already exists with the same ID, it's updated. If new, it's added. Old chunks that no longer correspond to any file are NOT automatically removed — use `--clear` for that.
