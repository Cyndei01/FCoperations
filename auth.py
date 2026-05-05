import os

import streamlit as st


def credentials_configured() -> bool:
    return bool(os.getenv("APP_USERNAME") and os.getenv("APP_PASSWORD"))


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def logout() -> None:
    st.session_state["authenticated"] = False
    st.session_state.pop("username", None)


def require_login() -> bool:
    if not credentials_configured():
        st.session_state["authenticated"] = True
        st.session_state.setdefault("username", "Local User")
        return True

    if is_authenticated():
        return True

    st.title("F&C Packaging")
    st.subheader("Internal Load Map Login")
    st.caption("Use your internal credentials to continue.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if not submitted:
        return False

    if username == os.getenv("APP_USERNAME") and password == os.getenv("APP_PASSWORD"):
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.rerun()

    st.error("Invalid username or password.")
    return False
