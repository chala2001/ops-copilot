# Ops-Copilot: Deep-Dive Architecture & Code Review

This document provides a line-by-line and block-by-block technical review of the Ops-Copilot system. It explains the "why" and "how" behind every major code segment.

---

## 1. Document Ingestion Pipeline (`ingest.py`)

The ingestion pipeline is the foundation of the RAG system. It transforms unstructured data into searchable mathematical vectors.

### 1.1 Multi-Source Loading
```python
from langchain_community.document_loaders import (
    DirectoryLoader, TextLoader, PyPDFLoader, ConfluenceLoader, GitLoader
)
```
*   **Code Review**: We use a modular loading strategy. Instead of writing custom scrapers, we leverage LangChain's community loaders.
*   **Example**: `ConfluenceLoader` handles OAuth/API token handshakes and converts HTML pages into plain text automatically, preserving page titles in metadata.

### 1.2 Recursive Character Splitting
```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)
```
*   **Why this logic?**: Simple splitting (every 1000 chars) often cuts sentences in half.
*   **Recursive Logic**: This splitter first tries to split by paragraphs (`\n\n`). If a paragraph is too big, it tries single newlines (`\n`). If still too big, it tries spaces. This ensures that **semantic context (sentences and paragraphs) stays together** as much as possible.
*   **Overlap (200)**: This creates a "sliding window." If a version number like `4.2.1` is at character 995, it will appear at the end of Chunk 1 AND the beginning of Chunk 2.

### 1.3 Vectorization & ChromaDB Storage
```python
embeddings = embedder.encode(texts, show_progress_bar=True).tolist()
collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
```
*   **Code Review**: We use `upsert` (Update + Insert). If you run the ingestion twice on the same file, it won't create duplicates; it will simply update the existing vectors.
*   **Database Example**:
    | ID | Vector (float32[384]) | Metadata | Content |
    | :--- | :--- | :--- | :--- |
    | `cusX_01` | `[0.1, -0.2, ...]` | `{"customer": "CustomerX"}` | "API Manager v4.2.1 installed on..." |

---

## 2. RAG Query Engine (`core/rag.py`)

This module handles the "Search" and "Reasoning" phases.

### 2.1 Filtered Retrieval (The Security Layer)
```python
if customer_scope:
    where_filter = {'customer': {'$in': customer_scope}}
results = collection.query(
    query_embeddings=[question_embedding],
    n_results=TOP_K_RESULTS,
    where=where_filter
)
```
*   **Code Review**: This is where **Multi-Tenancy** is enforced. 
*   **Detail**: Even if a document for "CustomerY" is mathematically the most similar to a query, ChromaDB will **ignore it** if `customer_scope` only contains `['CustomerX']`. This prevents data leakage between customer environments.

### 2.2 System Prompting (The "SRE Persona")
```python
system_prompt = '''You are an SRE assistant... 
RULES: 1. Answer ONLY from context. 2. If not in context, say so clearly...'''
```
*   **Why?**: LLMs like Gemini are prone to "hallucination" (making things up). By strictly defining these rules, we force the AI to act as a grounded interface to our documentation rather than a creative writer.

---

## 3. User Interface Logic (`app.py`)

The Streamlit app provides the front-end experience.

### 3.1 Session State Management
```python
if 'messages' not in st.session_state:
    st.session_state.messages = []
```
*   **Why?**: Streamlit is "stateless." Every time you click a button, the entire Python script runs from line 1 to the end. `session_state` is a special dictionary that persists data between these runs, allowing us to keep a chat history.

### 3.2 Dynamic Source Citations
```python
with st.expander(f'View {len(sources)} source(s)'):
    for src in sources:
        col3.text(f"{src['similarity']:.0%} match")
```
*   **Code Review**: We show a "similarity" percentage. This is calculated as `1 - distance`. A 95% match means the user's question and the documentation chunk are mathematically very close in meaning.

---

## 4. Evaluation Framework (`monitoring/evaluate.py`)

### 4.1 Gemini-to-Gemini Evaluation
```python
eval_llm = ChatGoogleGenerativeAI(model=LLM_MODEL, ...)
results = evaluate(dataset=dataset, metrics=[faithfulness, answer_relevancy], llm=eval_llm)
```
*   **The Logic**: We use one instance of Gemini to answer the question, and a *separate* instance of Gemini (the "Judge") to grade the answer.
*   **Metrics Explained**:
    - **Faithfulness**: The Judge checks every claim in the answer against the retrieved chunks. If the AI says "Version 5" but the docs say "Version 4," the faithfulness score drops.
    - **Answer Relevancy**: Measures if the answer actually helps the user or just repeats the question.

---

## 5. Summary of Data Flow

1.  **Raw File** (`.md`) → **Ingest** → **Text Chunks**.
2.  **Text Chunks** → **Embedding Model** → **Numerical Vectors**.
3.  **Numerical Vectors** → **ChromaDB** (Stored with Metadata).
4.  **User Question** → **Embedding Model** → **Search Vector**.
5.  **Search Vector** → **ChromaDB (Filtered by Customer)** → **Relevant Chunks**.
6.  **Relevant Chunks + Question** → **Gemini** → **Technical Answer**.
