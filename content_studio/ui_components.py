"""Small shared Streamlit presentation helpers."""

from __future__ import annotations

import streamlit as st


def render_page_header(title: str, description: str) -> None:
    """Render a consistent title and concise page description."""
    st.title(title)
    st.caption(description)


def render_empty_state(message: str, action_hint: str | None = None) -> None:
    """Render a restrained, text-first empty state."""
    st.info(message)
    if action_hint:
        st.caption(action_hint)


def render_operation_error(message: str, detail: str | None = None) -> None:
    """Render a user-safe error and optional non-sensitive diagnostic detail."""
    st.error(message)
    if detail:
        with st.expander("Technical details"):
            st.code(detail)
