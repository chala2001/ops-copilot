# app.py
# ── SRE Ops Copilot — Streamlit Chat Interface ──────────
# Run with: streamlit run app.py
 
import streamlit as st
from rag import ask, get_authorized_customers
 
# ── Page Configuration ────────────────────────────────────
# MUST be the very first Streamlit command in the file.
# layout='wide' uses the full browser width.
st.set_page_config(
    page_title='SRE Ops Copilot',
    page_icon='🔍',
    layout='wide',
    initial_sidebar_state='expanded'
)
 
# ── Custom CSS ────────────────────────────────────────────
# Small style tweaks to make the UI cleaner.
# Streamlit uses st.markdown with unsafe_allow_html=True for CSS.
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
 
# ── Sidebar ──────────────────────────────────────────────
# Everything inside 'with st.sidebar:' appears in the left panel.
with st.sidebar:
    st.title('SRE Ops Copilot')
    st.caption('AI-powered deployment knowledge base')
    st.divider()
 
    # ── User Selection ───────────────────────────────────
    # In a real production app, this comes from your SSO login.
    # For the internship demo, we let you pick the user.
    current_user = st.selectbox(
        'Logged in as',
        options=['alice', 'bob', 'carol', 'admin'],
        index=0
    )
 
    # Get the customers this user can access
    authorized_customers = get_authorized_customers(current_user)
 
    # ── Customer Scope Selector ──────────────────────────
    # Multi-select: the user can further narrow the search
    # to specific customers within their authorized set.
    customer_scope = st.multiselect(
        'Search within customers',
        options=authorized_customers,
        default=authorized_customers,
        help='Only documents for selected customers will be searched'
    )
 
    st.divider()
 
    # ── Suggested Questions ──────────────────────────────
    # Quick-start buttons for common queries.
    st.subheader('Try asking:')
    example_questions = [
        'What version is CustomerX running?',
        'What AKS node pool does CustomerX use?',
        'Who are the escalation contacts for CustomerX?',
        'Are there any known issues for CustomerX?',
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True, key=q):
            # When clicked, add to session state as if user typed it
            st.session_state['prefilled_question'] = q
 
    st.divider()
 
    # ── Clear Chat Button ────────────────────────────────
    if st.button('Clear conversation', use_container_width=True):
        st.session_state.messages = []
        st.rerun()  # Force page refresh to clear the chat display
 
# ── Main Chat Area ───────────────────────────────────────
st.header('SRE Knowledge Base')
st.caption(f'Searching as: {current_user} | Scope: {", ".join(customer_scope) if customer_scope else "None"}')
 
# ── Session State Initialization ─────────────────────────
# st.session_state is a dictionary that persists across reruns.
# Streamlit reruns the ENTIRE script on every user interaction.
# Without session_state, the chat history would vanish on every message.
if 'messages' not in st.session_state:
    st.session_state.messages = []
 
# ── Display Welcome Message ──────────────────────────────
if not st.session_state.messages:
    st.info(
        'Ask me anything about your customer deployments. '
        'I will search the knowledge base and cite my sources.'
    )
 
# ── Render All Chat History ──────────────────────────────
# Loop through all previous messages and display them.
# st.chat_message('user') shows a user avatar + bubble.
# st.chat_message('assistant') shows an assistant avatar + bubble.
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])
 
        # Show source citations for assistant messages
        if msg['role'] == 'assistant' and msg.get('sources'):
            sources = msg['sources']
            # Show top 3 sources as chips
            chips_html = ' '.join([
                f'<span class="source-chip">{s["source"].split("/")[-1]}</span>'
                for s in sources[:3]
            ])
            st.markdown(f'**Sources:** {chips_html}', unsafe_allow_html=True)
 
            # Show full details in a collapsible section
            with st.expander(f'View {len(sources)} source(s)'):
                for i, src in enumerate(sources):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.text(src['source'])
                    col2.text(src['customer'])
                    col3.text(f"{src['similarity']:.0%} match")
 
# ── Handle Pre-filled Question (from sidebar buttons) ────
# If a user clicked a suggested question, inject it
prefilled = st.session_state.pop('prefilled_question', None)
 
# ── Chat Input Box ────────────────────────────────────────
# st.chat_input renders a fixed input bar at the bottom.
# It returns None until the user submits (press Enter or click Send).
user_input = st.chat_input('Ask about any customer deployment...')
 
# Use prefilled question OR actual user input
prompt = prefilled or user_input
 
# ── Process New Question ──────────────────────────────────
if prompt:
    # Check that at least one customer is selected
    if not customer_scope:
        st.error('Select at least one customer from the sidebar.')
        st.stop()
 
    # 1. Display the user's question
    with st.chat_message('user'):
        st.write(prompt)
 
    # 2. Save user message to history
    st.session_state.messages.append({
        'role': 'user',
        'content': prompt
    })
 
    # 3. Call RAG and display answer
    with st.chat_message('assistant'):
        # Show a spinner while waiting for Claude's response
        with st.spinner('Searching knowledge base and generating answer...'):
            answer, sources = ask(prompt, customer_scope)
 
        # Display the answer
        st.write(answer)
 
        # Display source chips
        if sources:
            chips_html = ' '.join([
                f'<span class="source-chip">{s["source"].split("/")[-1]}</span>'
                for s in sources[:3]
            ])
            st.markdown(f'**Sources:** {chips_html}', unsafe_allow_html=True)
 
            with st.expander(f'View {len(sources)} source(s)'):
                for src in sources:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.text(src['source'])
                    col2.text(src['customer'])
                    col3.text(f"{src['similarity']:.0%} match")
 
    # 4. Save assistant response to history
    st.session_state.messages.append({
        'role': 'assistant',
        'content': answer,
        'sources': sources
    })