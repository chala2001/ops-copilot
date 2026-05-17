# core/ingest.py
# ── Document Ingestion Pipeline ─────────────────────────
# This module loads documents from multiple sources,
# splits them into chunks, converts them to vectors,
# and stores them in ChromaDB.

import os
import sys
from pathlib import Path

from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    ConfluenceLoader,
    GitLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

from core.config import (
    CHUNK_SIZE, CHUNK_OVERLAP, CHROMA_PATH,
    COLLECTION_NAME, EMBEDDING_MODEL,
    MARKDOWN_DIR, CONFLUENCE_DIR, PDF_DIR,
    CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY
)

import hashlib
import json
from datetime import datetime


STATE_FILE = 'ingestion_state.json'

def load_ingestion_state() -> dict:
    '''Load the record of previously ingested files.'''
    if not Path(STATE_FILE).exists():
        return {}
    with open(STATE_FILE) as f:
        return json.load(f).get('files', {})

def save_ingestion_state(state: dict):
    '''Save the updated file state after ingestion.'''
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'last_run': datetime.now().isoformat(),
            'total_files': len(state),
            'files': state
        }, f, indent=2)
    print(f'State saved: {len(state)} files tracked')

def file_hash(filepath: str) -> str:
    '''Compute MD5 hash of a file\'s contents.'''
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


# ── Step 1: Initialize the embedding model ───────────────
print('Loading embedding model...')
embedder = SentenceTransformer(EMBEDDING_MODEL)
print(f'Embedding model loaded: {EMBEDDING_MODEL}')

# ── Step 2: Initialize ChromaDB ──────────────────────────
print(f'Connecting to ChromaDB at {CHROMA_PATH}...')
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={'hnsw:space': 'cosine'}
)
print(f'Collection ready: {COLLECTION_NAME}')


def load_markdown_documents():
    md_path = Path(MARKDOWN_DIR)
    if not md_path.exists():
        print(f'No markdown folder found at {MARKDOWN_DIR}, skipping.')
        return []

    try:
        loader = DirectoryLoader(
            MARKDOWN_DIR,
            glob='**/*.md',
            loader_cls=TextLoader,
            show_progress=True
        )
        docs = loader.load()
        print(f'Loaded {len(docs)} markdown files')
        return docs

    except Exception as e:
        print(f'ERROR loading markdown files: {e}')
        return []


def load_pdf_documents():
    pdf_path = Path(PDF_DIR)
    if not pdf_path.exists():
        print(f'No pdf folder found at {PDF_DIR}, skipping.')
        return []

    all_docs = []
    for pdf_file in pdf_path.glob('**/*.pdf'):
        print(f'Loading PDF: {pdf_file.name}')
        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()
        all_docs.extend(docs)

    print(f'Loaded {len(all_docs)} PDF pages')
    return all_docs


def load_confluence_documents():
    if not CONFLUENCE_URL or 'your-company' in CONFLUENCE_URL:
        print('No valid CONFLUENCE_URL set. Skipping Confluence ingestion.')
        return []

    print(f'Connecting to Confluence: {CONFLUENCE_URL}')
    print(f'Loading space: {CONFLUENCE_SPACE_KEY}')

    try:
        loader = ConfluenceLoader(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            api_key=CONFLUENCE_API_TOKEN,
            space_key=CONFLUENCE_SPACE_KEY,
        )

        docs = loader.load()
        print(f'Loaded {len(docs)} Confluence pages')

        for doc in docs:
            doc.metadata['doc_type'] = 'confluence'
            title = doc.metadata.get('title', '').lower()
            if 'customerx' in title:
                doc.metadata['customer'] = 'CustomerX'
            elif 'customery' in title:
                doc.metadata['customer'] = 'CustomerY'
            else:
                doc.metadata['customer'] = 'General'

        return docs

    except Exception as e:
        print(f'Confluence error: {e}')
        return []


def load_github_documents(repo_path: str = './repos/sre-runbooks', branch: str = 'main'):
    if not Path(repo_path).exists():
        print(f'Repo not found at {repo_path}. Skipping GitHub ingestion.')
        return []

    print(f'Loading GitHub repo: {repo_path} (branch: {branch})')

    try:
        loader = GitLoader(
            repo_path=repo_path,
            branch=branch,
            file_filter=lambda path: path.endswith('.md'),
        )
        docs = loader.load()
        print(f'Loaded {len(docs)} files from GitHub repo')

        for doc in docs:
            doc.metadata['doc_type'] = 'github'
            file_path = doc.metadata.get('source', '').lower()
            if 'customerx' in file_path:
                doc.metadata['customer'] = 'CustomerX'
            else:
                doc.metadata['customer'] = 'General'

        return docs

    except Exception as e:
        print(f'GitHub loader error: {e}')
        return []


def add_customer_metadata(docs):
    for doc in docs:
        if 'customer' in doc.metadata:
            continue

        source = doc.metadata.get('source', '')
        filename = Path(source).name.lower()

        if 'customerx' in filename or 'customer_x' in filename:
            doc.metadata['customer'] = 'CustomerX'
        elif 'customery' in filename or 'customer_y' in filename:
            doc.metadata['customer'] = 'CustomerY'
        else:
            doc.metadata['customer'] = 'General'

        if filename.endswith('.md'):
            doc.metadata['doc_type'] = 'markdown'
        elif filename.endswith('.pdf'):
            doc.metadata['doc_type'] = 'pdf'
        else:
            doc.metadata['doc_type'] = 'other'

    return docs


def load_yaml_documents():
    yaml_path = Path('./data/yaml')
    if not yaml_path.exists():
        print('No yaml folder found at ./data/yaml, skipping.')
        return []

    import yaml
    all_docs = []

    from langchain_core.documents import Document

    for yaml_file in yaml_path.glob('**/*.yaml'):
        print(f'Loading YAML: {yaml_file.name}')
        try:
            with open(yaml_file, 'r') as f:
                yaml_docs = list(yaml.safe_load_all(f))

            for i, doc_content in enumerate(yaml_docs):
                if not doc_content:
                    continue

                text_content = f"# Kubernetes Configuration: {yaml_file.name} (Document {i+1})\n\n"
                text_content += yaml.dump(doc_content, default_flow_style=False)

                doc = Document(
                    page_content=text_content,
                    metadata={
                        'source': str(yaml_file),
                        'doc_type': 'yaml',
                        'filename': yaml_file.name,
                        'yaml_index': i
                    }
                )
                all_docs.append(doc)

        except Exception as e:
            print(f'Error loading {yaml_file.name}: {e}')
            continue

    print(f'Loaded {len(all_docs)} YAML files')
    return all_docs


def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )

    chunks = splitter.split_documents(docs)
    print(f'Split {len(docs)} documents into {len(chunks)} chunks')
    return chunks


def store_in_chromadb(chunks):
    if not chunks:
        print('No chunks to store.')
        return

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    ids = []
    for i, chunk in enumerate(chunks):
        source = chunk.metadata.get('source', 'unknown')
        filename = Path(source).stem
        chunk_id = f'{filename}_chunk_{i}'
        ids.append(chunk_id)

    print(f'Converting {len(texts)} chunks to vectors...')
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f'Stored {len(chunks)} chunks in ChromaDB')
    print(f'Total chunks in database: {collection.count()}')


def clear_collection():
    global collection
    count = collection.count()
    print(f'Clearing {count} chunks from ChromaDB...')

    chroma_client.delete_collection(COLLECTION_NAME)
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={'hnsw:space': 'cosine'}
    )
    print('Collection cleared and recreated.')


def run_ingestion():
    print('=' * 50)
    print('Starting document ingestion pipeline')
    print('=' * 50)

    all_docs = []
    all_docs.extend(load_markdown_documents())
    all_docs.extend(load_pdf_documents())
    all_docs.extend(load_yaml_documents())

    all_docs = add_customer_metadata(all_docs)

    if not all_docs:
        print('No documents found to ingest.')
        return

    chunks = split_documents(all_docs)
    store_in_chromadb(chunks)

    print('=' * 50)
    print('Ingestion complete!')
    print('=' * 50)

    state = load_ingestion_state()
    for doc in all_docs:
        source = doc.metadata.get('source', 'unknown')
        if Path(source).exists():
            state[source] = file_hash(source)
    save_ingestion_state(state)
