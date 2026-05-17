# ingest.py - CLI entry point for document ingestion
# Run: python ingest.py [--clear]
import sys
from core.ingest import run_ingestion, clear_collection

if __name__ == '__main__':
    if '--clear' in sys.argv:
        clear_collection()
    run_ingestion()
