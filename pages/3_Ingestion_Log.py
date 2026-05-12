# pages/3_Ingestion_Log.py

import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path

# pages/3_Ingestion_Log.py

import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title='Ingestion Log', 
    page_icon='📥', 
    layout='wide'
)

# ──────────────────────────────────────────────────────────
# AUTHENTICATION CHECK
# ──────────────────────────────────────────────────────────
from auth import check_login

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

if not st.session_state.authenticated:
    st.warning('🔒 Please log in to access this page.')
    st.info('👉 Go to the main Chat page to log in.')
    
    st.divider()
    st.subheader('Login')
    
    with st.form('login_form'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        submit = st.form_submit_button('Sign in')
    
    if submit:
        if username and password:
            user_info = check_login(username, password)
            if user_info:
                st.session_state.authenticated = True
                st.session_state.user_info = user_info
                st.success('✅ Login successful!')
                st.rerun()
            else:
                st.error('❌ Invalid credentials')
        else:
            st.error('❌ Please enter username and password')
    
    st.stop()

user_info = st.session_state.user_info
st.sidebar.success(f"✓ Logged in as: {user_info['display_name']}")

if st.sidebar.button('Sign out'):
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.rerun()
# ──────────────────────────────────────────────────────────

st.title('📥 Ingestion Log')
# ... rest of your existing code ...
st.caption('Document ingestion status and history')

STATE_FILE = 'ingestion_state.json'

# ── Load state ────────────────────────────────────────────
if not os.path.exists(STATE_FILE):
    st.info('No ingestion has run yet.')
    st.code('python ingest.py', language='bash')
    st.stop()

with open(STATE_FILE) as f:
    state = json.load(f)

# ── Show summary ──────────────────────────────────────────
last_run = datetime.fromisoformat(state['last_run'])

col1, col2 = st.columns(2)
col1.metric('Last ingestion', last_run.strftime('%Y-%m-%d %H:%M'))
col2.metric('Total files tracked', state['total_files'])

# ── Show file list ────────────────────────────────────────
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

# ── Manual re-ingestion with exception handling ───────────
st.divider()
st.subheader('Manual Actions')

col_a, col_b = st.columns(2)

with col_a:
    if st.button('🔄 Re-ingest all files', type='primary'):
        with st.spinner('Running ingestion... This may take 30-60 seconds'):
            try:
                import subprocess
                import sys
                
                # Use sys.executable to get the correct Python path
                result = subprocess.run(
                    [sys.executable, 'ingest.py'],
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                    cwd=os.getcwd()  # Ensure correct working directory
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
                import sys
                
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