# tests/test_ingest.py
import sys
import os
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest import load_markdown_documents, split_documents, add_customer_metadata
from config import CHUNK_SIZE

def test_markdown_loading():
    '''Test that markdown files load correctly.'''
    docs = load_markdown_documents()
    # In a fresh environment, we might not have docs, so we check if it returns a list
    assert isinstance(docs, list)
    print(f'Found {len(docs)} markdown files')

def test_chunking():
    '''Test that chunking produces appropriate chunk sizes.'''
    # Create a mock document
    class MockDoc:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata

    docs = [MockDoc('A' * (CHUNK_SIZE * 2), {'source': 'test.md'})]
    chunks = split_documents(docs)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.page_content) <= CHUNK_SIZE * 1.1
    print(f'PASS: Chunking works as expected')

def test_metadata():
    '''Test that customer metadata is added correctly.'''
    class MockDoc:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata

    docs = [
        MockDoc('info', {'source': 'customerX_data.md'}),
        MockDoc('info', {'source': 'general_info.md'})
    ]
    docs = add_customer_metadata(docs)
    assert docs[0].metadata['customer'] == 'CustomerX'
    assert docs[1].metadata['customer'] == 'General'
    print('PASS: Metadata assignment works correctly')

if __name__ == '__main__':
    print('Running ingestion tests...')
    test_markdown_loading()
    test_chunking()
    test_metadata()
    print('\nAll tests passed!')
