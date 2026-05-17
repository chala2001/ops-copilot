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
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

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
# How many document chunks to retrieve per question
# More chunks = more context but slower and more expensive
TOP_K_RESULTS = 5

# ── Data Folders ─────────────────────────────────────────
MARKDOWN_DIR = './data/markdown'
CONFLUENCE_DIR = './data/confluence'
PDF_DIR = './data/pdf'
