# pages/4_Usage_Dashboard.py
# Query analytics and system usage dashboard

import streamlit as st
import pandas as pd
from datetime import datetime
from monitoring.logger import load_log

st.set_page_config(
    page_title='Usage Dashboard',
    page_icon='📈',
    layout='wide'
)

from auth.auth_guard import require_authentication
user_info = require_authentication()

# ── Page content ──────────────────────────────────────────
st.title('📈 Usage Dashboard')
st.caption('Query analytics and system usage')

queries = load_log()

if not queries:
    st.info('No queries logged yet. Ask some questions in the chat!')
    st.stop()

df = pd.DataFrame(queries)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date

col1, col2, col3, col4 = st.columns(4)
col1.metric('Total queries', len(df))
col2.metric('Unique users', df['username'].nunique())
col3.metric('Avg latency', f"{df['latency_ms'].mean():.0f} ms")
col4.metric('Success rate', f"{df['success'].mean():.1%}")

st.divider()

st.subheader('Queries per day')
daily = df.groupby('date').size().reset_index(name='count')
st.bar_chart(daily.set_index('date')['count'])

st.subheader('Response Time Distribution (ms)')
st.bar_chart(df['latency_ms'].head(50))

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

st.divider()
st.subheader('Recent queries (last 20)')
recent = df[['timestamp', 'username', 'question', 'latency_ms', 'success']]
recent = recent.sort_values('timestamp', ascending=False).head(20)
st.dataframe(recent, use_container_width=True)

failed = df[df['success'] == False]
if not failed.empty:
    st.divider()
    st.subheader(f'⚠️ Failed queries ({len(failed)})')
    st.dataframe(
        failed[['timestamp', 'username', 'question', 'error']],
        use_container_width=True
    )
