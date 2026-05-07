# Ops-Copilot: Detailed System Architecture

This document provides a comprehensive explanation of the Ops-Copilot Gemini RAG (Retrieval-Augmented Generation) system, detailing each component, the data flow, and the database structure.

## 1. High-Level Architecture

The system is built on a modular RAG architecture designed for SRE (Site Reliability Engineering) teams. It consists of four main layers:

1.  **Ingestion Layer**: Pulls data from multi-sources (Local, Confluence, GitHub).
2.  **Storage Layer**: Vector database (ChromaDB) storing embedded text chunks.
3.  **RAG Query Engine**: Processes questions, retrieves context, and generates answers using Gemini.
4.  **Evaluation Layer**: Measures the quality of answers using RAGAS metrics.

---

## 2. Ingestion Pipeline (`ingest.py`)

The ingestion pipeline is responsible for turning raw documents into searchable vectors.

### Code Breakdown:
- **`load_markdown_documents()` / `load_pdf_documents()`**: Uses LangChain loaders to walk through local directories and extract text.
- **`load_confluence_documents()`**: Uses `ConfluenceLoader` to call the Atlassian API and download pages from specific spaces.
- **`load_github_documents()`**: Uses `GitLoader` to clone or read a local repository and extract documentation.
- **`add_customer_metadata()`**: A critical step that adds a `customer` tag to each document.
    - *Example*: If a file is named `customerX_runbook.md`, it adds `metadata['customer'] = 'CustomerX'`.
- **`split_documents()`**: Breaks long documents into smaller chunks (e.g., 1000 characters) with overlap (200 characters).
- **`store_in_chromadb()`**: Converts text to vectors using the `all-MiniLM-L6-v2` model and saves them.

### Data Example (What is stored in ChromaDB?):
For each chunk, ChromaDB stores:
- **ID**: `customerX_runbook_chunk_5`
- **Vector**: `[0.12, -0.45, 0.78, ...]` (384-dimensional array)
- **Document (Text)**: `"The WSO2 API Manager version for CustomerX is 4.2.1. It runs on AKS."`
- **Metadata**: `{"customer": "CustomerX", "doc_type": "markdown", "source": "data/markdown/customerX_runbook.md"}`

---

## 3. RAG Query Engine (`rag.py`)

This is the "brain" of the application that interacts with the user.

### Code Breakdown:
- **`ask(question, customer_scope)`**:
    1.  **Vectorization**: Converts the user's question into a vector using the *same* model used during ingestion.
    2.  **Filtered Retrieval**: Queries ChromaDB with a `where` filter.
        - *Example Filter*: `{'customer': {'$in': ['CustomerX', 'General']}}`
        - *Benefit*: Ensures Bob can't see Customer Y's secrets.
    3.  **Context Construction**: Combines the top 5 most relevant chunks into a single "Context Block".
    4.  **Gemini Prompting**: Sends the context and question to Gemini Flash.
- **`get_authorized_customers(username)`**: A security helper that maps a user's ID to the customer documents they are allowed to see.

---

## 4. Evaluation Framework (`evaluate.py`)

This script ensures the AI is actually giving good advice.

### Code Breakdown:
- **RAGAS Integration**: Uses the RAGAS library but swaps out the default OpenAI components for Gemini.
- **`faithfulness` Metric**: Checks if the AI's answer is supported *only* by the retrieved context (prevents hallucinations).
- **`answer_relevancy` Metric**: Checks if the answer actually addresses the user's question.
- **Gemini Evaluator**: Uses `ChatGoogleGenerativeAI` and `GoogleGenerativeAIEmbeddings` to run these checks without needing an OpenAI key.

---

## 5. Security & Access Control

The system implements **Metadata-Level Authorization**:
1.  Every document is tagged with a `customer` name during ingestion.
2.  Every user is mapped to a list of allowed `customers`.
3.  Every search query is restricted by ChromaDB's `where` clause to only show authorized chunks.

---

## 6. Troubleshooting: Rate Limits (429 Errors)

If you see a `429 RESOURCE_EXHAUSTED` error:
- **Cause**: The Gemini Free Tier has a limit of **20 requests per minute** for `gemini-3-flash`.
- **Solution**: 
    1.  Wait 30-60 seconds and retry.
    2.  The `evaluate.py` script now has a `time.sleep(2)` to slow down requests.
    3.  Reduce the number of `EVAL_QUESTIONS` if you are hitting daily project limits.
