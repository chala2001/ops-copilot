# pages/2_Evaluation_Dashboard.py
# Evaluation quality dashboard

import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title='Evaluation Dashboard', 
    page_icon='📊', 
    layout='wide'
)

st.title('📊 RAG Quality Dashboard')
st.caption('Run: python evaluate.py  to update these scores.')

RESULTS_FILE = 'evaluation_results.json'

# ── Load results ──────────────────────────────────────────
if not os.path.exists(RESULTS_FILE):
    st.warning(
        '⚠️ No evaluation results found. '
        'Run: `python evaluate.py` to generate scores.'
    )
    st.code('python evaluate.py', language='bash')
    st.stop()

with open(RESULTS_FILE) as f:
    data = json.load(f)

# ── Show timestamp ────────────────────────────────────────
ts = datetime.fromisoformat(data['timestamp'])
st.caption(
    f"Last evaluated: {ts.strftime('%Y-%m-%d %H:%M')} | "
    f"{data['num_questions']} questions | "
    f"Model: {data.get('model', 'gemini-flash-latest')}"
)

# ── Top-level metrics ─────────────────────────────────────
col1, col2 = st.columns(2)

faith = data['faithfulness']
rel = data['answer_relevancy']

# Show green if above target, red if below
col1.metric(
    label='Faithfulness',
    value=f'{faith:.1%}',
    delta='Above target' if faith > 0.85 else 'Below target (0.85)',
    delta_color='normal' if faith > 0.85 else 'inverse'
)
col2.metric(
    label='Answer Relevancy',
    value=f'{rel:.1%}',
    delta='Above target' if rel > 0.80 else 'Below target (0.80)',
    delta_color='normal' if rel > 0.80 else 'inverse'
)

st.divider()

# ── Per-question breakdown ────────────────────────────────
st.subheader('Per-Question Scores')

if 'per_question' in data:
    import pandas as pd
    df = pd.DataFrame(data['per_question'])
    
    # Color-code each score cell
    def color_score(val):
        if val > 0.75:
            color = 'green'
        elif val > 0.5:
            color = 'orange'
        else:
            color = 'red'
        return f'color: {color}; font-weight: bold'
    
    styled = df.style.applymap(
        color_score,
        subset=['faithfulness', 'answer_relevancy']
    ).format({
        'faithfulness': '{:.1%}',
        'answer_relevancy': '{:.1%}'
    })
    
    st.dataframe(styled, use_container_width=True)

# ── Interpretation guide ─────────────────────────────────
with st.expander('How to interpret these scores'):
    st.write('''
    **Faithfulness** measures whether Gemini's answer is grounded
    in the retrieved context. A score of 1.0 means every claim
    in the answer is supported by the documents. A low score means
    Gemini is hallucinating — making up facts not in the documents.
    **Fix:** improve your chunking so context is more complete.
    
    **Answer Relevancy** measures whether the answer actually addresses
    the question. A low score means Gemini went off-topic.
    **Fix:** improve your system prompt to be more specific.
    ''')

# ── Re-run button ─────────────────────────────────────────
st.divider()
if st.button('🔄 Re-run evaluation now', type='primary'):
    with st.spinner('Running evaluation... This takes 2-3 minutes'):
        import subprocess
        result = subprocess.run(
            ['python', 'evaluate.py'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            st.success('✅ Evaluation complete! Refresh this page.')
        else:
            st.error(f'Error: {result.stderr}')