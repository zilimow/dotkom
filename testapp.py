import  streamlit as st

if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

with st.sidebar:
    st.subheader("Admin")
    
    st.html("""
        <style>
            div[data-testid="stTextInputRootElement"] button {
                display: none !important;
            }
        </style>
    """)
    
    placeholder = st.container()
    
    with placeholder:
        if not st.session_state['is_admin']:
            secret_key = st.text_input(
                "Enter Key", 
                type="password", 
                key="admin_key", 
                label_visibility="collapsed",
                placeholder="Enter password..."
            )
            if secret_key == "secret123":
                st.session_state['is_admin'] = True
                st.rerun()
        else:
            # use_container_width makes it fill the sidebar completely
            if st.button("Log out", use_container_width=True):
                st.session_state['is_admin'] = False
                st.rerun()
