# core/rag.py
# ── RAG Query Engine ────────────────────────────────────
# This module handles all queries:
#   1. Embed the question
#   2. Search ChromaDB for relevant chunks
#   3. Build a prompt with the retrieved context
#   4. Ask Gemini for an answer
#   5. Return the answer + source information

from google import genai
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from core.config import (
    GOOGLE_API_KEY, LLM_MODEL, EMBEDDING_MODEL,
    CHROMA_PATH, COLLECTION_NAME, TOP_K_RESULTS,
    RERANK_ENABLED, RETRIEVAL_TOP_N, RERANKER_MODEL,
    BGE_QUERY_PREFIX,
)

# ── Initialize once at module load ───────────────────────
print('Initializing RAG engine...')

# Gemini API client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Embedding model (same one used in ingest.py — must match!)
embedder = SentenceTransformer(EMBEDDING_MODEL)

# Cross-encoder for reranking. Reads (query, chunk) together and gives a
# relevance score — slower than vector search but much more accurate, so
# we only run it on the top N candidates from stage 1.
reranker = CrossEncoder(RERANKER_MODEL) if RERANK_ENABLED else None

# Connect to ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

def get_collection():
    # Fetch the collection fresh on every call. Avoids stale references when
    # another process (e.g. `python ingest.py --clear`) deletes and recreates
    # the collection — which gives it a new internal UUID.
    return chroma_client.get_or_create_collection(name=COLLECTION_NAME)

print(f'RAG engine ready. Database has {get_collection().count()} chunks. '
      f'Reranking: {"on" if RERANK_ENABLED else "off"}.')


def _embed_query(question: str) -> list:
    """Encode a query with the BGE prefix it was trained to expect."""
    return embedder.encode(BGE_QUERY_PREFIX + question).tolist()


def _retrieve(question: str, customer_scope: list) -> tuple:
    """
    Two-stage retrieval:
      1. Vector search → RETRIEVAL_TOP_N candidates (or TOP_K_RESULTS if rerank off)
      2. Cross-encoder rerank → keep top TOP_K_RESULTS
    Returns (chunks, metadatas, similarities).
    """
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return [], [], []

    stage1_k = RETRIEVAL_TOP_N if RERANK_ENABLED else TOP_K_RESULTS
    n_results = min(stage1_k, total)

    where_filter = {'customer': {'$in': customer_scope}} if customer_scope else None

    results = collection.query(
        query_embeddings=[_embed_query(question)],
        n_results=n_results,
        where=where_filter,
        include=['documents', 'metadatas', 'distances'],
    )

    chunks    = results['documents'][0]
    metas     = results['metadatas'][0]
    distances = results['distances'][0]

    if not chunks:
        return [], [], []

    # Convert ChromaDB cosine distance to a similarity score in [0, 1]
    similarities = [round(1 - d, 3) for d in distances]

    if not RERANK_ENABLED or reranker is None:
        return chunks, metas, similarities

    # ── Stage 2: rerank with cross-encoder ────────────────
    # The cross-encoder scores each (question, chunk) pair directly.
    # Higher score = more relevant. We keep the top TOP_K_RESULTS.
    pairs = [(question, chunk) for chunk in chunks]
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(scores, chunks, metas, similarities),
        key=lambda x: x[0],
        reverse=True,
    )[:TOP_K_RESULTS]

    chunks       = [r[1] for r in ranked]
    metas        = [r[2] for r in ranked]
    similarities = [r[3] for r in ranked]
    return chunks, metas, similarities

# ── Access Control ───────────────────────────────────────
USER_PERMISSIONS = {
    'alice': ['CustomerX', 'CustomerY', 'General'],
    'bob':   ['CustomerX', 'General'],
    'carol': ['CustomerY', 'General'],
    'admin': ['CustomerX', 'CustomerY', 'General'],
}

def get_authorized_customers(username: str) -> list:
    return USER_PERMISSIONS.get(username, ['General'])

# ── Core RAG Function ────────────────────────────────────
def ask(question: str, customer_scope: list) -> tuple:
    '''
    Main RAG query function.
    '''

    # ── Input validation ──────────────────────────────────
    if not question or not question.strip():
        return ('Please provide a question.', [])

    if len(question) > 2000:
        return ('Question too long. Please keep it under 2000 characters.', [])

    if not customer_scope:
        return ('No customer scope selected. Please select at least one customer.', [])

    if get_collection().count() == 0:
        return ('The knowledge base is empty. Please run: python ingest.py', [])

    # ── Step 1+2: Retrieve and (optionally) rerank ───────
    retrieved_chunks, retrieved_metadata, similarities = _retrieve(question, customer_scope)

    if not retrieved_chunks:
        return ('I could not find relevant information for that query. '
                'Try rephrasing or check if the documents are ingested.', [])

    # ── Step 3: Build the context string ─────────────────
    context_parts = []
    for i, (chunk, meta) in enumerate(zip(retrieved_chunks, retrieved_metadata)):
        source = meta.get('source', 'Unknown')
        customer = meta.get('customer', 'General')
        context_parts.append(
            f'[Source {i+1}: {source} | Customer: {customer}]\n{chunk}'
        )

    context = '\n\n---\n\n'.join(context_parts)

    # ── Step 4: Build the prompt ──────────────────────────
    system_prompt = '''You are an SRE (Site Reliability Engineer) assistant
for the WSO2 operations team. You have access to internal deployment
documentation for customer environments.

RULES:
1. Answer ONLY from the provided context. Do not use outside knowledge.
2. If the answer is not in the context, say so clearly.
3. Always mention specific versions, configurations, and values.
4. Keep answers concise and technically precise.
5. If there are known issues or workarounds, mention them.
6. Reference the source document when giving an answer.'''

    user_message = f'''Context from deployment documentation:

{context}

Question: {question}

Answer based only on the context above:'''

    # ── Step 5: Call Gemini API with error handling ───────
    full_prompt = f"{system_prompt}\n\n{user_message}"

    try:
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=full_prompt
        )
        answer = response.text

    except Exception as e:
        # Catch Gemini API errors
        error_msg = str(e)
        if '429' in error_msg:
            answer = ('Rate limit reached. Please wait a moment and try again. '
                     '(Gemini free tier: 15 requests per minute)')
        elif 'API key' in error_msg or 'authentication' in error_msg.lower():
            answer = 'API authentication failed. Check your GOOGLE_API_KEY in .env file.'
        else:
            answer = f'Error generating response: {error_msg}'

        return answer, []

    # ── Step 6: Return answer + sources ──────────────────
    sources = []
    for chunk, meta, sim in zip(retrieved_chunks, retrieved_metadata, similarities):
        sources.append({
            'content': chunk,
            'source': meta.get('source', 'Unknown'),
            'customer': meta.get('customer', 'General'),
            'doc_type': meta.get('doc_type', 'unknown'),
            'similarity': sim,
        })

    return answer, sources


def ask_stream(question: str, customer_scope: list):
    '''
    Streaming version of ask().
    Yields text pieces one by one as Gemini generates them,
    then yields the sources list as the final item.
    '''

    # ── Step 1: Retrieve relevant chunks (with rerank if enabled) ─
    retrieved_chunks, retrieved_metadata, similarities = _retrieve(question, customer_scope)

    if not retrieved_chunks:
        yield 'I could not find relevant information for that query.'
        return

    # ── Step 2: Build context ─────────────────────────────
    context_parts = []
    for i, (chunk, meta) in enumerate(zip(retrieved_chunks, retrieved_metadata)):
        source   = meta.get('source',   'Unknown')
        customer = meta.get('customer', 'General')
        context_parts.append(
            f'[Source {i+1}: {source} | Customer: {customer}]\n{chunk}'
        )
    context = '\n\n---\n\n'.join(context_parts)

    system_prompt = '''You are an SRE assistant for the WSO2 operations team.
Answer ONLY from the provided context. If the answer is not in the context, say so.
Be concise, precise, and always mention version numbers and specific values.'''

    user_message = f'''Context:\n{context}\n\nQuestion: {question}
\nAnswer based only on the context above:'''

    # ── Step 3: Call Gemini in STREAMING mode ─────────────
    full_prompt = f"{system_prompt}\n\n{user_message}"

    response = client.models.generate_content_stream(
        model=LLM_MODEL,
        contents=full_prompt
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text

    # ── Step 4: Yield sources after all text ──────────────
    sources = []
    for meta, sim in zip(retrieved_metadata, similarities):
        sources.append({
            'source':     meta.get('source',   'Unknown'),
            'customer':   meta.get('customer', 'General'),
            'doc_type':   meta.get('doc_type', 'unknown'),
            'similarity': sim,
        })
    yield sources


def test_rag():
    print('\nRunning test query...')
    test_q = 'What version of WSO2 API Manager is CustomerX running?'
    answer, sources = ask(test_q, ['CustomerX', 'General'])
    print(f'Question: {test_q}')
    print(f'Answer: {answer}')
    print(f'Sources: {[s["source"] for s in sources]}')

if __name__ == '__main__':
    test_rag()
