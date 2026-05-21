# core/config.py
# ── All project settings in one place ──────────────────
import os
from dotenv import load_dotenv

# Load the .env file so variables are available
load_dotenv()

# ── API Settings ─────────────────────────────────────────
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CONFLUENCE_URL = os.getenv('CONFLUENCE_URL', '')
CONFLUENCE_USERNAME = os.getenv('CONFLUENCE_USERNAME', '')
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_API_TOKEN', '')
CONFLUENCE_SPACE_KEY = os.getenv('CONFLUENCE_SPACE_KEY', 'SRE')

# ── Model Settings ───────────────────────────────────────
# The Gemini model to use for answering questions
LLM_MODEL = 'gemini-flash-latest'

# The local embedding model that converts text to vectors
# This runs on your computer, no API key needed, completely free
# EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
EMBEDDING_MODEL = 'BAAI/bge-base-en-v1.5'

# ── Document Chunking Settings ───────────────────────────
# How many characters per chunk (roughly 300-500 words)
CHUNK_SIZE = 1000

# How many characters overlap between adjacent chunks
# Overlap helps avoid cutting off context at chunk boundaries
CHUNK_OVERLAP = 200

# ── ChromaDB Settings ────────────────────────────────────
# Folder where ChromaDB saves its data
CHROMA_PATH = './chroma_db'

# The 'collection' name inside ChromaDB (like a table name)
COLLECTION_NAME = 'ops_knowledge'

# ── Retrieval Settings ───────────────────────────────────
# Final number of chunks passed to the LLM as context.
TOP_K_RESULTS = 5

# ── Reranking Settings ───────────────────────────────────
# Two-stage retrieval:
#   1. Vector search returns RETRIEVAL_TOP_N candidates (wide net, fast).
#   2. Cross-encoder reranks them and keeps the best TOP_K_RESULTS.
# Set RERANK_ENABLED = False to skip stage 2 and revert to plain vector search.
RERANK_ENABLED = True
RETRIEVAL_TOP_N = 20
RERANKER_MODEL = 'BAAI/bge-reranker-base'

# BGE embedding models expect a specific prefix on the query side only.
# Documents are embedded without any prefix.
BGE_QUERY_PREFIX = 'Represent this sentence for searching relevant passages: '

# ── Data Folders ─────────────────────────────────────────
MARKDOWN_DIR = './data/markdown'
CONFLUENCE_DIR = './data/confluence'
PDF_DIR = './data/pdf'
