# logger.py - Query Logger with Complete Exception Handling

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOG_FILE = 'query_log.json'

def log_query(
    username: str,
    question: str,
    customer_scope: list,
    answer: str,
    sources: list,
    latency_ms: int,
    success: bool = True,
    error: Optional[str] = None
):
    '''
    Append a query record to the log file with complete error handling.
    '''
    try:
        # Validate inputs
        if not username:
            username = "unknown"
        if not question:
            question = ""
        if not isinstance(customer_scope, list):
            customer_scope = []
        if not isinstance(sources, list):
            sources = []
        
        # Build record
        try:
            record = {
                'timestamp':      datetime.now().isoformat(),
                'username':       str(username),
                'question':       str(question)[:500],  # Limit length
                'customer_scope': 'ALL',
                'answer_length':  len(answer) if answer else 0,
                'num_sources':    len(sources),
                'latency_ms':     int(latency_ms) if latency_ms else 0,
                'success':        bool(success),
                'error':          str(error) if error else None,
                'top_source':     sources[0].get('source', 'Unknown') if sources else None,
            }
        except Exception as record_error:
            logger.error(f"Error building log record: {record_error}")
            return  # Fail silently to not disrupt user experience
        
        # Load existing log
        try:
            if Path(LOG_FILE).exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    log = json.load(f)
                    if not isinstance(log, dict) or 'queries' not in log:
                        logger.warning("Invalid log file structure, recreating")
                        log = {'queries': []}
            else:
                log = {'queries': []}
        except json.JSONDecodeError:
            logger.warning("Corrupt log file, recreating")
            log = {'queries': []}
        except Exception as load_error:
            logger.error(f"Error loading log file: {load_error}")
            log = {'queries': []}
        
        # Append new record
        try:
            log['queries'].append(record)
        except Exception as append_error:
            logger.error(f"Error appending to log: {append_error}")
            return
        
        # Save back to file
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(log, f, indent=2, ensure_ascii=False)
        except Exception as save_error:
            logger.error(f"Error saving log file: {save_error}")
            return
    
    except Exception as e:
        logger.error(f"Unexpected error in log_query: {e}")
        # Fail silently to not disrupt user experience

def load_log() -> List[Dict[str, Any]]:
    '''Load all query records from the log file with error handling.'''
    try:
        if not Path(LOG_FILE).exists():
            logger.info(f"Log file {LOG_FILE} does not exist yet")
            return []
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            log = json.load(f)
        
        if not isinstance(log, dict):
            logger.warning("Invalid log file format")
            return []
        
        queries = log.get('queries', [])
        
        if not isinstance(queries, list):
            logger.warning("Invalid queries format in log")
            return []
        
        return queries
    
    except json.JSONDecodeError as e:
        logger.error(f"Corrupt log file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading log: {e}")
        return []