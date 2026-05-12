# pages/5_Admin_Panel.py
# Admin panel for user management

import streamlit as st
import json
import hashlib
from auth_guard import require_authentication

st.set_page_config(
    page_title='Admin Panel', 
    page_icon='⚙️', 
    layout='wide'
)

# Require authentication
user_info = require_authentication()

# Only admins can access
if user_info.get('role') != 'admin':
    st.error('🔒 Admin access required')
    st.info('This page is only accessible to administrators.')
    st.stop()

st.title('⚙️ Admin Panel')
st.caption('User management and system administration')

# Load users
try:
    with open('users.json', 'r') as f:
        data = json.load(f)
        users = data['users']
except Exception as e:
    st.error(f'Error loading users: {e}')
    st.stop()

# Display current users
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

# Add new user
st.divider()
st.subheader('Add New User')

col1, col2 = st.columns(2)

with col1:
    with st.form('add_user'):
        new_username = st.text_input('Username', help='Lowercase, no spaces')
        new_password = st.text_input('Password', type='password')
        new_display = st.text_input('Display Name', help='Full name with role')
        new_role = st.selectbox('Role', ['sre', 'senior_sre', 'admin'])
        
        submit = st.form_submit_button('Add User', type='primary', use_container_width=True)
        
        if submit:
            if new_username and new_password and new_display:
                if new_username in users:
                    st.error('❌ Username already exists')
                else:
                    try:
                        # Hash password
                        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
                        
                        # Add user
                        users[new_username] = {
                            'password_hash': password_hash,
                            'display_name': new_display,
                            'customers': ['ALL'],
                            'role': new_role
                        }
                        
                        # Save
                        data['users'] = users
                        with open('users.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        
                        st.success(f'✅ User {new_username} added successfully!')
                        st.balloons()
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f'❌ Error adding user: {e}')
            else:
                st.error('❌ Please fill all fields')

with col2:
    st.info('''
    **Password Guidelines:**
    - Minimum 8 characters
    - Mix of letters and numbers
    - Avoid common words
    
    **Role Types:**
    - **sre**: Regular SRE team member
    - **senior_sre**: Senior SRE with additional privileges
    - **admin**: Full system access including user management
    
    **Access:**
    - All users have access to ALL customer documents
    ''')

# Delete user section
st.divider()
st.subheader('Remove User')

col1, col2 = st.columns(2)

with col1:
    with st.form('delete_user'):
        delete_username = st.selectbox(
            'Select user to remove',
            options=[u for u in users.keys() if u != user_info['username']],
            help='Cannot delete your own account'
        )
        
        confirm = st.checkbox('I understand this action cannot be undone')
        delete_submit = st.form_submit_button('Delete User', type='secondary')
        
        if delete_submit:
            if not confirm:
                st.error('❌ Please confirm deletion')
            elif delete_username:
                try:
                    del users[delete_username]
                    
                    data['users'] = users
                    with open('users.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    st.success(f'✅ User {delete_username} removed')
                    st.rerun()
                
                except Exception as e:
                    st.error(f'❌ Error deleting user: {e}')

with col2:
    st.warning('''
    **⚠️ Warning:**
    - Deleting a user is permanent
    - The user will lose access immediately
    - Their query history will remain in logs
    - You cannot delete your own account
    ''')

# System info
st.divider()
st.subheader('System Information')

col1, col2, col3 = st.columns(3)

try:
    import os
    from pathlib import Path
    
    # Query logs
    if Path('query_log.json').exists():
        with open('query_log.json') as f:
            log_data = json.load(f)
            total_queries = len(log_data.get('queries', []))
    else:
        total_queries = 0
    
    # Documents
    doc_count = 0
    for doc_dir in ['data/markdown', 'data/pdf', 'data/yaml']:
        if Path(doc_dir).exists():
            doc_count += sum(1 for _ in Path(doc_dir).rglob('*') if _.is_file())
    
    col1.metric('Total Users', len(users))
    col2.metric('Total Queries', total_queries)
    col3.metric('Documents Ingested', doc_count)

except Exception as e:
    st.warning(f'Could not load system stats: {e}')
