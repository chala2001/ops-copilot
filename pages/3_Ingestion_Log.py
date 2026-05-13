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

from auth_guard import require_authentication
user_info = require_authentication()

# ── Page content ──────────────────────────────────────────
st.title('📥 Ingestion Log')
st.caption('Document ingestion status and history')

STATE_FILE = 'ingestion_state.json'

if not os.path.exists(STATE_FILE):
    st.info('No ingestion has run yet.')
    st.code('python ingest.py', language='bash')
    st.stop()

with open(STATE_FILE) as f:
    state = json.load(f)

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
                    [sys.executable, 'ingest.py'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=os.getcwd()
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
                    [sys.executable, 'ingest.py', '--clear'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=os.getcwd()
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
