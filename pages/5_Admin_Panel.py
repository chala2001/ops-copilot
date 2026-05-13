# pages/5_Admin_Panel.py
# Admin panel for user management
# SECURITY: Now uses auth.create_user() which hashes with bcrypt.
# The old version used hashlib.sha256 directly — that is now removed.

import streamlit as st
import json
from pathlib import Path
from auth_guard import require_authentication
from auth import create_user, delete_user, load_users

st.set_page_config(
    page_title='Admin Panel',
    page_icon='⚙️',
    layout='wide'
)

# Require authentication first — this stops unauthenticated access
user_info = require_authentication()

# Only admins can proceed past this point
if user_info.get('role') != 'admin':
    st.error('🔒 Admin access required')
    st.info('This page is only accessible to administrators.')
    st.stop()

st.title('⚙️ Admin Panel')
st.caption('User management and system administration')

# ── Load and display current users ────────────────────────────────────────────
try:
    users = load_users()
except Exception as e:
    st.error(f'Error loading users: {e}')
    st.stop()

st.subheader('Current Users')

try:
    import pandas as pd

    user_list = []
    for username, info in users.items():
        user_list.append({
            'Username': username,
            'Display Name': info.get('display_name', 'N/A'),
            'Role': info.get('role', 'N/A'),
            'Access': ', '.join(info.get('customers', ['General']))
        })

    df = pd.DataFrame(user_list)
    st.dataframe(df, use_container_width=True)
    st.metric('Total Users', len(users))

except Exception as e:
    st.error(f'Error displaying users: {e}')

# ── Add new user ──────────────────────────────────────────────────────────────
st.divider()
st.subheader('Add New User')

col1, col2 = st.columns(2)

with col1:
    with st.form('add_user'):
        new_username = st.text_input('Username', help='Lowercase, no spaces')
        new_password = st.text_input('Password', type='password')
        confirm_password = st.text_input('Confirm Password', type='password')
        new_display = st.text_input('Display Name', help='Full name with role, e.g. "Alice (SRE)"')
        new_role = st.selectbox('Role', ['sre', 'senior_sre', 'admin'])

        submit = st.form_submit_button('Add User', type='primary', use_container_width=True)

        if submit:
            if not new_username or not new_password or not new_display:
                st.error('❌ Please fill all required fields')
            elif new_password != confirm_password:
                st.error('❌ Passwords do not match')
            elif len(new_password) < 8:
                st.error('❌ Password must be at least 8 characters')
            elif ' ' in new_username:
                st.error('❌ Username cannot contain spaces')
            else:
                # create_user() in auth.py hashes the password with bcrypt
                # before saving. No SHA-256 anywhere.
                success = create_user(
                    username=new_username.lower().strip(),
                    password=new_password,
                    display_name=new_display,
                    role=new_role
                )
                if success:
                    st.success(f'✅ User {new_username} added successfully!')
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f'❌ Username "{new_username}" already exists')

with col2:
    st.info('''
    **Password Requirements:**
    - Minimum 8 characters
    - Mix of uppercase, lowercase, numbers, symbols recommended
    - Avoid common words or patterns

    **Role Types:**
    - **sre**: Regular SRE team member
    - **senior_sre**: Senior SRE with additional privileges
    - **admin**: Full system access including user management

    **Security Note:**
    Passwords are hashed with bcrypt (cost factor 12) before storage.
    The plain-text password is never saved anywhere.
    ''')

# ── Delete user ───────────────────────────────────────────────────────────────
st.divider()
st.subheader('Remove User')

col1, col2 = st.columns(2)

with col1:
    with st.form('delete_user'):
        deletable_users = [u for u in users.keys() if u != user_info['username']]

        if not deletable_users:
            st.info('No other users to delete.')
            st.form_submit_button('Delete User', disabled=True)
        else:
            delete_username = st.selectbox(
                'Select user to remove',
                options=deletable_users,
                help='Cannot delete your own account'
            )
            confirm = st.checkbox('I understand this action cannot be undone')
            delete_submit = st.form_submit_button('Delete User', type='secondary')

            if delete_submit:
                if not confirm:
                    st.error('❌ Please confirm deletion by checking the box')
                else:
                    success = delete_user(delete_username)
                    if success:
                        st.success(f'✅ User {delete_username} removed')
                        st.rerun()
                    else:
                        st.error(f'❌ Could not delete user {delete_username}')

with col2:
    st.warning('''
    **⚠️ Warning:**
    - Deleting a user is permanent
    - The user will lose access immediately
    - Their query history will remain in logs
    - You cannot delete your own account
    ''')

# ── System info ───────────────────────────────────────────────────────────────
st.divider()
st.subheader('System Information')

col1, col2, col3 = st.columns(3)

try:
    log_file = Path('query_log.json')
    if log_file.exists():
        with open(log_file) as f:
            log_data = json.load(f)
            total_queries = len(log_data.get('queries', []))
    else:
        total_queries = 0

    doc_count = 0
    for doc_dir in ['data/markdown', 'data/pdf', 'data/yaml']:
        if Path(doc_dir).exists():
            doc_count += sum(1 for _ in Path(doc_dir).rglob('*') if _.is_file())

    col1.metric('Total Users', len(users))
    col2.metric('Total Queries', total_queries)
    col3.metric('Documents Ingested', doc_count)

except Exception as e:
    st.warning(f'Could not load system stats: {e}')