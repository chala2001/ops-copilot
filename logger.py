# logger.py
# ── Query Logger ────────────────────────────────────────
# Logs every query with timing, user, and result info.

import json
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = 'query_log.json'

def log_query(
    username: str,
    question: str,
    customer_scope: list,
    answer: str,
    sources: list,
    latency_ms: int,
    success: bool = True,
    error: str = None
):
    '''
    Append a query record to the log file.
    
    Args:
        username:       Who asked the question
        question:       The question text
        customer_scope: Which customers were searched
        answer:         Gemini's answer
        sources:        List of source dicts returned by rag.py
        latency_ms:     How long the query took in milliseconds
        success:        False if an error occurred
        error:          Error message if success=False
    '''
    record = {
        'timestamp':      datetime.now().isoformat(),
        'username':       username,
        'question':       question,
        'customer_scope': customer_scope,
        'answer_length':  len(answer),
        'num_sources':    len(sources),
        'latency_ms':     latency_ms,
        'success':        success,
        'error':          error,
        # Store the top source for quick analysis
        'top_source':     sources[0]['source'] if sources else None,
    }
    
    # Load existing log
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            log = json.load(f)
    else:
        log = {'queries': []}
    
    # Append new record
    log['queries'].append(record)
    
    # Save back
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

def load_log() -> list:
    '''Load all query records from the log file.'''
    if not Path(LOG_FILE).exists():
        return []
    with open(LOG_FILE) as f:
        return json.load(f).get('queries', [])