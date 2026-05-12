# auth_guard.py
# Reusable authentication guard for dashboard pages

import streamlit as st
from auth import check_login

def require_authentication():
    '''
    Call this at the top of every dashboard page.
    Returns user_info if authenticated, otherwise shows login and stops.
    '''
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None
    
    if not st.session_state.authenticated:
        st.warning('🔒 Access Denied - Authentication Required')
        st.info('👉 Please log in to access this dashboard.')
        
        st.divider()
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader('🔐 Login')
            
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
                        st.success('✅ Login successful!')
                        st.rerun()
                    else:
                        st.error('❌ Invalid credentials')
                else:
                    st.error('❌ Please enter username and password')
        
        st.stop()
    
    user_info = st.session_state.user_info
    
    with st.sidebar:
        st.success(f"✓ {user_info['display_name']}")
        if st.button('🚪 Sign out', use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.rerun()
    
    return user_info
