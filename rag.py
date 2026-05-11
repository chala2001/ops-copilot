# rag.py
# ── RAG Query Engine ────────────────────────────────────
# This module handles all queries:
#   1. Embed the question
#   2. Search ChromaDB for relevant chunks
#   3. Build a prompt with the retrieved context
#   4. Ask Gemini for an answer
#   5. Return the answer + source information

from google import genai
import chromadb
from sentence_transformers import SentenceTransformer
from config import (
    GOOGLE_API_KEY, LLM_MODEL, EMBEDDING_MODEL,
    CHROMA_PATH, COLLECTION_NAME, TOP_K_RESULTS
)

# ── Initialize once at module load ───────────────────────
print('Initializing RAG engine...')

# Gemini API client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Embedding model (same one used in ingest.py — must match!)
embedder = SentenceTransformer(EMBEDDING_MODEL)

# Connect to ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

print(f'RAG engine ready. Database has {collection.count()} chunks.')

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

    # ── Step 1: Convert question to a vector ─────────────
    question_embedding = embedder.encode(question).tolist()

    # ── Step 2: Search ChromaDB ───────────────────────────
    if customer_scope:
        where_filter = {'customer': {'$in': customer_scope}}
    else:
        where_filter = None

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(TOP_K_RESULTS, collection.count()) if collection.count() > 0 else 0,
        where=where_filter,
        include=['documents', 'metadatas', 'distances']
    )

    if not results['documents'] or not results['documents'][0]:
        return ('I could not find relevant information for that query. '
                'Try rephrasing or check if the documents are ingested.', [])

    retrieved_chunks = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    distances = results['distances'][0]

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

    # ── Step 5: Call Gemini API ───────────────────────────
    full_prompt = f"{system_prompt}\n\n{user_message}"
    
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=full_prompt
    )

    answer = response.text

    # ── Step 6: Return answer + sources ──────────────────
    sources = []
    for chunk, meta, dist in zip(retrieved_chunks, retrieved_metadata, distances):
        sources.append({
            'content': chunk,
            'source': meta.get('source', 'Unknown'),
            'customer': meta.get('customer', 'General'),
            'doc_type': meta.get('doc_type', 'unknown'),
            'similarity': round(1 - dist, 3)
        })

    return answer, sources

# ADD THIS FUNCTION to rag.py, below the existing ask() function
 
def ask_stream(question: str, customer_scope: list):
    '''
    Streaming version of ask().
    Instead of returning (answer, sources) all at once,
    this function is a GENERATOR that yields text pieces one by one.
 
    A generator is a special Python function that uses 'yield' instead
    of 'return'. When you call a generator, you get an iterator back.
    Each time you call next() on the iterator, it runs until the next yield.
 
    Usage in app.py:
        for text_piece in ask_stream(question, scope):
            print(text_piece, end='', flush=True)
 
    Args:
        question:       The user's question
        customer_scope: List of customer names the user can access
 
    Yields:
        str: Small pieces of the answer text as they are generated
        dict: At the very end, yields the sources list
    '''
 
    # ── Step 1: Retrieve relevant chunks (same as ask()) ──
    question_embedding = embedder.encode(question).tolist()
 
    if customer_scope:
        where_filter = {'customer': {'$in': customer_scope}}
    else:
        where_filter = None
 
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(TOP_K_RESULTS, collection.count()),
        where=where_filter,
        include=['documents', 'metadatas', 'distances']
    )
 
    retrieved_chunks   = results['documents'][0]
    retrieved_metadata = results['metadatas'][0]
    distances          = results['distances'][0]
 
    if not retrieved_chunks:
        # Yield an error message and stop
        yield 'I could not find relevant information for that query.'
        return
 
    # ── Step 2: Build context (same as ask()) ─────────────
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
    
    # Gemini's streaming response
    response = client.models.generate_content_stream(
        model=LLM_MODEL,
        contents=full_prompt
    )
    
    # Yield each text chunk as it arrives
    for chunk in response:
        if chunk.text:
            yield chunk.text
    # ── Step 4: After all text is yielded, yield the sources ──
    # We yield sources as a special marker so app.py knows
    # when streaming is done and what sources to display.
    sources = []
    for meta, dist in zip(retrieved_metadata, distances):
        sources.append({
            'source':     meta.get('source',   'Unknown'),
            'customer':   meta.get('customer', 'General'),
            'doc_type':   meta.get('doc_type', 'unknown'),
            'similarity': round(1 - dist, 3)
        })
    # Yield sources as a dict — app.py checks the type to detect this
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