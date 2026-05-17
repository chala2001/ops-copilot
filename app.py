# app.py
# ── SRE Ops Copilot — Streamlit Chat Interface ──────────
# Run with: streamlit run app.py

import streamlit as st
from core.rag import ask, ask_stream, get_authorized_customers
import time
from monitoring.logger import log_query
from auth.session_manager import check_session_timeout, init_session_tracking, logout_user

st.set_page_config(
    page_title='SRE Ops Copilot',
    page_icon='🔍',
    layout='wide',
    initial_sidebar_state='expanded'
)

from auth.auth import check_login, get_user_customers as auth_get_customers

# ── Session State ─────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

# ── Login Gate ────────────────────────────────────────────
if not st.session_state.authenticated:
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.title('🔍 SRE Ops Copilot')
        st.subheader('Sign in to continue')
        st.divider()

        with st.form('login_form'):
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            submit = st.form_submit_button('Sign in', use_container_width=True)

        if submit:
            if not username or not password:
                st.error('Please enter both username and password.')
            else:
                user_info = check_login(username, password)
                if user_info:
                    st.session_state.authenticated = True
                    st.session_state.user_info = user_info
                    init_session_tracking()
                    st.rerun()
                else:
                    st.error('Incorrect username or password.')
    st.stop()

# ── Authenticated ─────────────────────────────────────────
user_info = st.session_state.user_info
current_user = user_info['username']

session_valid, timeout_message = check_session_timeout()
if not session_valid:
    st.warning(timeout_message)
    logout_user()
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.divider()
        if st.button('🔒 Click here to log in again', type='primary', use_container_width=True):
            st.rerun()
    st.stop()

# ── Custom CSS ────────────────────────────────────────────
st.markdown('''
<style>
    .source-chip {
        background: #E8F0FE;
        border: 1px solid #C5D0EF;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 12px;
        margin-right: 6px;
        color: #1B4F8A;
        display: inline-block;
    }
</style>
''', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────
from core.rag import collection
from auth.session_manager import display_session_status

with st.sidebar:
    st.title('SRE Ops Copilot')
    st.caption('AI-powered deployment knowledge base')
    st.divider()

    st.success(f"✓ {user_info['display_name']}")
    if st.button('Sign out'):
        logout_user()
        st.rerun()

    display_session_status()
    st.metric('Knowledge chunks', collection.count())
    st.divider()

    st.info('🔓 **Full Access Mode**\nSearch across all customer documents')
    st.divider()

    st.subheader('Try asking:')
    example_questions = [
        'What version is CustomerX running?',
        'What AKS node pool does CustomerX use?',
        'Who are the escalation contacts for CustomerX?',
        'Are there any known issues for CustomerX?',
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True, key=q):
            st.session_state['prefilled_question'] = q

    st.divider()

    if st.button('Clear conversation', use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Main Chat Area ────────────────────────────────────────
st.header('SRE Knowledge Base')
st.caption(f'Searching as: {current_user} | Access: All Customers')

if 'messages' not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.info(
        'Ask me anything about your customer deployments. '
        'I will search the knowledge base and cite my sources.'
    )

for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])

        if msg['role'] == 'assistant' and msg.get('sources'):
            sources = msg['sources']
            chips_html = ' '.join([
                f'<span class="source-chip">{s["source"].split("/")[-1]}</span>'
                for s in sources[:3]
            ])
            st.markdown(f'**Sources:** {chips_html}', unsafe_allow_html=True)

            with st.expander(f'View {len(sources)} source(s)'):
                for i, src in enumerate(sources):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.text(src['source'])
                    col2.text(src['customer'])
                    col3.text(f"{src['similarity']:.0%} match")

prefilled = st.session_state.pop('prefilled_question', None)
user_input = st.chat_input('Ask about any customer deployment...')
prompt = prefilled or user_input

if prompt:
    from auth.rate_limiter import check_query_rate_limit

    query_allowed, rate_message = check_query_rate_limit(current_user)
    if not query_allowed:
        st.error(rate_message)
        st.info('💡 Rate limits ensure fair API usage across the team.')
        st.stop()

    with st.chat_message('user'):
        st.write(prompt)

    st.session_state.messages.append({'role': 'user', 'content': prompt})

    with st.chat_message('assistant'):
        sources_holder = []

        def text_only_stream():
            for piece in ask_stream(prompt, customer_scope=None):
                if isinstance(piece, list):
                    sources_holder.extend(piece)
                else:
                    yield piece

        start_time = time.time()

        try:
            full_answer = st.write_stream(text_only_stream())
            success = True
            error_msg = None
        except Exception as e:
            full_answer = f'Error generating answer: {e}'
            st.error(full_answer)
            success = False
            error_msg = str(e)

        latency_ms = int((time.time() - start_time) * 1000)
        sources = sources_holder

        log_query(
            username=current_user,
            question=prompt,
            customer_scope=['ALL'],
            answer=full_answer,
            sources=sources,
            latency_ms=latency_ms,
            success=success,
            error=error_msg
        )

    st.session_state.messages.append({
        'role': 'assistant',
        'content': full_answer,
        'sources': sources
    })

# ── Footer ────────────────────────────────────────────────
st.divider()
st.caption('SRE Ops Copilot · Powered by Gemini · Answers are grounded in retrieved documentation only.')
