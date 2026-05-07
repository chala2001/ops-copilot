# tests/test_rag.py
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import ask, get_authorized_customers

# Test cases: questions with expected keywords in answers (if data exists)
TEST_CASES = [
    {
        'question': 'What version of WSO2 API Manager is CustomerX running?',
        'customer_scope': ['CustomerX'],
        'description': 'Version number retrieval'
    },
    {
        'question': 'What are the known issues for CustomerX?',
        'customer_scope': ['CustomerX'],
        'description': 'Known issues retrieval'
    },
]

def test_rag_query():
    '''Test that the RAG query function returns expected structure.'''
    for case in TEST_CASES:
        print(f'\nTesting: {case["description"]}')
        answer, sources = ask(case['question'], case['customer_scope'])
        
        assert isinstance(answer, str)
        assert isinstance(sources, list)
        print(f'PASS: Received answer and {len(sources)} sources')

def test_access_control():
    '''Test that access control filters work at the function level.'''
    # This just verifies the permission mapping function
    authorized = get_authorized_customers('bob')
    assert 'CustomerX' in authorized
    assert 'CustomerY' not in authorized
    print('PASS: Access control permissions correctly mapped')

if __name__ == '__main__':
    print('Running RAG tests...')
    test_rag_query()
    test_access_control()
    print('\nAll tests passed!')
