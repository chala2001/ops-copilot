# pages/2_Evaluation_Dashboard.py
# Evaluation quality dashboard with authentication and exception handling

import streamlit as st
import json
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title='Evaluation Dashboard', 
    page_icon='📊', 
    layout='wide'
)

# ──────────────────────────────────────────────────────────
# AUTHENTICATION CHECK
# ──────────────────────────────────────────────────────────
from auth import check_login

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

# Check if user is logged in
if not st.session_state.authenticated:
    st.warning('🔒 Please log in to access this page.')
    st.info('👉 Go to the main Chat page to log in.')
    
    # Show login form
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader('Login')
        
        with st.form('login_form'):
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            submit = st.form_submit_button('Sign in', use_container_width=True)
        
        if submit:
            if username and password:
                user_info = check_login(username, password)
                if user_info:
                    st.session_state.authenticated = True
                    st.session_state.user_info = user_info
                    st.success('✅ Login successful! Redirecting...')
                    st.rerun()
                else:
                    st.error('❌ Invalid credentials')
            else:
                st.error('❌ Please enter username and password')
    
    st.stop()  # Stop rendering the page

# User is authenticated - show their info
user_info = st.session_state.user_info
st.sidebar.success(f"✓ Logged in as: {user_info['display_name']}")

if st.sidebar.button('Sign out'):
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.rerun()
# ──────────────────────────────────────────────────────────
# END AUTHENTICATION CHECK
# ──────────────────────────────────────────────────────────

st.title('📊 RAG Quality Dashboard')
st.caption('Run: python evaluate.py to update these scores.')

RESULTS_FILE = 'evaluation_results.json'

# ── Load results with exception handling ──────────────────
try:
    if not os.path.exists(RESULTS_FILE):
        st.warning(
            '⚠️ No evaluation results found. '
            'Run: `python evaluate.py` to generate scores.'
        )
        st.code('python evaluate.py', language='bash')
        st.info('💡 This will take 2-3 minutes and requires an active internet connection.')
        st.stop()

    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in results file: {e}")
    st.error('❌ Results file is corrupted. Please run `python evaluate.py` again.')
    st.stop()
except Exception as e:
    logger.error(f"Error loading results: {e}")
    st.error(f'❌ Error loading results: {e}')
    st.stop()

# ── Show timestamp with exception handling ────────────────
try:
    ts = datetime.fromisoformat(data['timestamp'])
    st.caption(
        f"Last evaluated: {ts.strftime('%Y-%m-%d %H:%M')} | "
        f"{data.get('num_questions', 0)} questions | "
        f"Model: {data.get('model', 'gemini-flash-latest')}"
    )
except (KeyError, ValueError) as e:
    logger.warning(f"Timestamp parsing error: {e}")
    st.caption("Evaluation results loaded")

# ── Top-level metrics with exception handling ─────────────
try:
    col1, col2 = st.columns(2)

    faith = data.get('faithfulness', 0)
    rel = data.get('answer_relevancy', 0)

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

except (KeyError, TypeError, ValueError) as e:
    logger.error(f"Error displaying metrics: {e}")
    st.error('❌ Error displaying metrics. Results file may be incomplete.')

# ── Per-question breakdown with exception handling ────────
try:
    st.subheader('Per-Question Scores')

    if 'per_question' in data and data['per_question']:
        import pandas as pd
        
        try:
            df = pd.DataFrame(data['per_question'])
            
            # Color-code each score cell
            def color_score(val):
                try:
                    if val > 0.75:
                        color = 'green'
                    elif val > 0.5:
                        color = 'orange'
                    else:
                        color = 'red'
                    return f'color: {color}; font-weight: bold'
                except:
                    return ''
            
            styled = df.style.applymap(
                color_score,
                subset=['faithfulness', 'answer_relevancy']
            ).format({
                'faithfulness': '{:.1%}',
                'answer_relevancy': '{:.1%}'
            })
            
            st.dataframe(styled, use_container_width=True)
        
        except Exception as df_error:
            logger.error(f"Error creating dataframe: {df_error}")
            st.warning('⚠️ Could not display per-question breakdown')
            st.json(data.get('per_question', []))
    else:
        st.info('No per-question data available')

except Exception as e:
    logger.error(f"Error in per-question section: {e}")
    st.warning('⚠️ Error displaying per-question scores')

# ── Interpretation guide ─────────────────────────────────
try:
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
except Exception as e:
    logger.error(f"Error displaying interpretation: {e}")

# ── Re-run button with exception handling ─────────────────
try:
    st.divider()
    if st.button('🔄 Re-run evaluation now', type='primary'):
        with st.spinner('Running evaluation... This takes 2-3 minutes'):
            try:
                import subprocess
                
                # Use sys.executable for correct Python interpreter
                result = subprocess.run(
                    [sys.executable, 'evaluate.py'],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    cwd=os.getcwd()
                )
                
                if result.returncode == 0:
                    st.success('✅ Evaluation complete! Refreshing page...')
                    st.rerun()
                else:
                    st.error('❌ Evaluation failed')
                    with st.expander('Error details'):
                        st.code(result.stderr, language='text')
                        
            except subprocess.TimeoutExpired:
                st.error('⏱️ Evaluation timed out after 5 minutes')
            except FileNotFoundError:
                st.error('❌ evaluate.py not found')
            except Exception as btn_error:
                logger.error(f"Error running evaluation: {btn_error}")
                st.error(f'❌ Error: {btn_error}')
                
except Exception as e:
    logger.error(f"Error in re-run section: {e}")