import streamlit as st

if 'current_user' not in st.session_state:  
    st.session_state.current_user = 'None'

person_names = ["User1", "User2"]

def callback_function():# Diese Funktion wird aufgerufen, wenn der Benutzer eine neue Person auswählt
    # Logging Message
    print(f"The user has changed to {st.session_state.current_user}") 
    # Manuelles wieder ausführen
    #st.rerun()

st.session_state.current_user = st.selectbox(
    'Versuchsperson',
    options = person_names, key="sbVersuchsperson", on_change = callback_function)
