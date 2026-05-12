# pages/4_Usage_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime
from logger import load_log

# pages/4_Usage_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime
from logger import load_log

st.set_page_config(
    page_title='Usage Dashboard', 
    page_icon='📈', 
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

st.title('📈 Usage Dashboard')
# ... rest of your existing code ...
st.caption('Query analytics and system usage')

# ── Load query log ────────────────────────────────────────
queries = load_log()

if not queries:
    st.info('No queries logged yet. Ask some questions in the chat!')
    st.stop()

df = pd.DataFrame(queries)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date

# ── Top KPIs ─────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

col1.metric('Total queries', len(df))
col2.metric('Unique users', df['username'].nunique())
col3.metric('Avg latency', f"{df['latency_ms'].mean():.0f} ms")
col4.metric('Success rate', f"{df['success'].mean():.1%}")

st.divider()

# ── Queries per day chart ─────────────────────────────────
st.subheader('Queries per day')
daily = df.groupby('date').size().reset_index(name='count')
st.bar_chart(daily.set_index('date')['count'])

# ── Latency distribution ──────────────────────────────────
st.subheader('Response Time Distribution (ms)')
st.bar_chart(df['latency_ms'].head(50))

# ── Two-column layout ─────────────────────────────────────
col_users, col_sources = st.columns(2)

with col_users:
    st.subheader('Queries by user')
    user_counts = df['username'].value_counts().reset_index()
    user_counts.columns = ['User', 'Queries']
    st.dataframe(user_counts, use_container_width=True)

with col_sources:
    st.subheader('Most retrieved sources')
    source_counts = df['top_source'].value_counts().head(10).reset_index()
    source_counts.columns = ['Source', 'Times retrieved']
    st.dataframe(source_counts, use_container_width=True)

# ── Recent queries ────────────────────────────────────────
st.divider()
st.subheader('Recent queries (last 20)')
recent = df[['timestamp', 'username', 'question', 'latency_ms', 'success']]
recent = recent.sort_values('timestamp', ascending=False).head(20)
st.dataframe(recent, use_container_width=True)

# ── Failed queries ────────────────────────────────────────
failed = df[df['success'] == False]
if not failed.empty:
    st.divider()
    st.subheader(f'⚠️ Failed queries ({len(failed)})')
    st.dataframe(
        failed[['timestamp', 'username', 'question', 'error']],
        use_container_width=True
    )