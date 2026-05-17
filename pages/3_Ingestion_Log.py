# pages/3_Ingestion_Log.py
# Ingestion log and manual re-ingestion controls

import streamlit as st
import json
import os
import sys
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title='Ingestion Log',
    page_icon='📥',
    layout='wide'
)

from auth.auth_guard import require_authentication
user_info = require_authentication()

# ── Page content ──────────────────────────────────────────
st.title('📥 Ingestion Log')
st.caption('Document ingestion status and history')

# Project root is two levels up from this file (pages/3_Ingestion_Log.py → pages/ → project root)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
VENV_PYTHON = PROJECT_ROOT / 'venv' / 'bin' / 'python3'
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

STATE_FILE = PROJECT_ROOT / 'ingestion_state.json'

if not STATE_FILE.exists():
    st.info('No ingestion has run yet.')
    st.code('python ingest.py', language='bash')
    st.stop()

if not STATE_FILE.is_file():
    st.error('Expected ingestion_state.json to be a file, but the path points to a directory.')
    st.caption('Remove or rename the directory at ingestion_state.json, then run ingestion again.')
    st.stop()

try:
    with open(str(STATE_FILE)) as f:
        state = json.load(f)
except json.JSONDecodeError:
    st.error('The ingestion_state.json file is not valid JSON.')
    st.caption('Delete or replace ingestion_state.json and re-run ingestion to recreate it.')
    st.stop()
except Exception as e:
    st.error(f'Unable to read ingestion_state.json: {e}')
    st.stop()

last_run = datetime.fromisoformat(state['last_run'])

col1, col2 = st.columns(2)
col1.metric('Last ingestion', last_run.strftime('%Y-%m-%d %H:%M'))
col2.metric('Total files tracked', state['total_files'])

st.divider()
st.subheader('Tracked Files')

import pandas as pd

files_data = []
for filepath, hash_val in state['files'].items():
    p = Path(filepath)
    files_data.append({
        'File': p.name,
        'Path': str(p.parent),
        'Hash (first 8)': hash_val[:8],
        'Exists': '✅' if p.exists() else '❌'
    })

df = pd.DataFrame(files_data)
st.dataframe(df, use_container_width=True)

st.divider()
st.subheader('Manual Actions')

col_a, col_b = st.columns(2)

with col_a:
    if st.button('🔄 Re-ingest all files', type='primary'):
        with st.spinner('Running ingestion... This may take 30-60 seconds'):
            try:
                import subprocess

                result = subprocess.run(
                    [PYTHON_EXE, 'ingest.py'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(PROJECT_ROOT)
                )

                if result.returncode == 0:
                    st.success('✅ Ingestion complete! Refresh page to see updates.')
                    st.code(result.stdout, language='text')
                else:
                    st.error('❌ Ingestion failed')
                    with st.expander('Error details'):
                        st.code(result.stderr, language='text')

            except subprocess.TimeoutExpired:
                st.error('⏱️ Ingestion timed out after 2 minutes')
            except FileNotFoundError:
                st.error('❌ ingest.py not found. Make sure you are in the project directory.')
            except Exception as e:
                st.error(f'❌ Unexpected error: {e}')

with col_b:
    if st.button('🗑️ Clear database and re-ingest', type='secondary'):
        with st.spinner('Clearing database and re-ingesting... This may take 30-60 seconds'):
            try:
                import subprocess

                result = subprocess.run(
                    [PYTHON_EXE, 'ingest.py', '--clear'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(PROJECT_ROOT)
                )

                if result.returncode == 0:
                    st.success('✅ Database cleared and re-ingested!')
                    st.code(result.stdout, language='text')
                else:
                    st.error('❌ Operation failed')
                    with st.expander('Error details'):
                        st.code(result.stderr, language='text')

            except subprocess.TimeoutExpired:
                st.error('⏱️ Operation timed out after 2 minutes')
            except FileNotFoundError:
                st.error('❌ ingest.py not found')
            except Exception as e:
                st.error(f'❌ Unexpected error: {e}')
