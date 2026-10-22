"""Streamlit entry point and base navigation for AI Crypto Content Studio."""

from __future__ import annotations

import streamlit as st

from content_studio.config import get_settings
from content_studio.database import init_db
from content_studio.models import MarketSnapshot, ResearchBundle, ResearchSource
from content_studio.quality_agent import check_content
from content_studio.repositories import get_draft, list_drafts, update_draft
from content_studio.research_agent import collect_research
from content_studio.ui_components import render_page_header
from content_studio.workflow_service import generate_and_save_draft
from content_studio.writer_agent import WriterConfigurationError, WriterProviderError


def render_content_workspace() -> None:
    """Render the currently implemented research and draft workspace."""
    settings = get_settings()
    init_db(settings.database_path)

    if "research_bundle" not in st.session_state:
        st.session_state.research_bundle = None
    if "active_draft_id" not in st.session_state:
        st.session_state.active_draft_id = None
    if "draft_editor_value" not in st.session_state:
        st.session_state.draft_editor_value = ""

    render_page_header(
        "AI Crypto Content Studio",
        "Research a finance or crypto topic, generate an evidence-backed draft, and review it before publication.",
    )

    with st.sidebar:
        st.header("Setup status")
        if settings.text_ai_configured:
            st.success(
                f"Text AI configured · {settings.ai_provider.title()} · {settings.selected_model}"
            )
        else:
            st.warning("Text AI not configured")
            st.caption("Copy `.env.example` to `.env`, add GROQ_API_KEY, and restart the app.")
        st.write(f"RSS sources configured: **{len(settings.rss_feeds)}**")
        st.write(
            f"Public market data: **{'Enabled' if settings.market_data_enabled else 'Disabled'}**"
        )
        st.write("Binance publishing: **Not implemented in this milestone**")
        st.write("Image generation: **Not implemented in this milestone**")
        st.divider()
        st.markdown("**Milestone plan**")
        st.markdown(
            "1. Research + writing — in progress\n2. Image generation\n3. Review and approval UX\n4. Binance Square publishing\n5. Scheduling and deployment"
        )

    with st.expander("Before you start", expanded=not settings.text_ai_configured):
        st.markdown("""
        1. Install dependencies from `requirements.txt`.
        2. Copy `.env.example` to `.env`.
        3. Keep `AI_PROVIDER=groq` and add a Groq API key from [Groq Console](https://console.groq.com/keys).
        4. Run `streamlit run app.py`.

        Research uses configured RSS feeds. Public market-data calls do not require a private Binance trading key.
        This version does **not** publish anything to Binance Square and does **not** generate images yet.
        """)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("1. Research a topic")
        topic = st.text_input(
            "Topic",
            value="Bitcoin market analysis",
            help="Use a specific topic such as Bitcoin, Ethereum, Solana, or a named announcement.",
        )
        category = st.selectbox(
            "Content category",
            [
                "Market and price analysis",
                "Crypto education",
                "Blockchain technology",
                "Verified crypto news",
                "Financial literacy",
                "Crypto security and risk awareness",
            ],
        )
        if st.button("Research topic", type="primary", use_container_width=True):
            if not topic.strip():
                st.error("Enter a topic first.")
            else:
                try:
                    with st.spinner("Checking RSS sources and public market data…"):
                        result = collect_research(topic, category, settings)
                    st.session_state.research_bundle = result.to_dict()
                    st.session_state.active_draft_id = None
                    st.session_state.draft_editor_value = ""
                    if result.sources:
                        st.success(
                            f"Research complete: {len(result.sources)} directly relevant source(s)."
                        )
                    else:
                        st.warning(
                            "No directly relevant sources found. Choose a suggested topic below or adjust your topic."
                        )
                except Exception as exc:
                    st.error(
                        f"Research failed ({type(exc).__name__}). Check your network and RSS feed settings."
                    )

    with right:
        st.subheader("2. Generate the draft")
        tone = st.selectbox(
            "Writing tone",
            [
                "Clear and educational",
                "Professional and analytical",
                "Beginner-friendly",
                "Concise and engaging",
            ],
        )
        target_length = st.selectbox(
            "Target length",
            ["Short (100–180 words)", "Medium (180–300 words)", "Detailed (300–500 words)"],
        )
        research_dict = st.session_state.research_bundle
        can_generate = bool(
            research_dict and research_dict.get("sources") and settings.text_ai_configured
        )
        if not settings.text_ai_configured:
            st.info(
                f"Add the API key for the configured provider ({settings.ai_provider}) to enable real AI drafting. No dummy response will be used."
            )
        elif not research_dict or not research_dict.get("sources"):
            st.info(
                "Run research first. Draft generation is disabled until at least one directly relevant source is found."
            )
        if st.button(
            "Generate draft from research", disabled=not can_generate, use_container_width=True
        ):
            try:
                bundle = ResearchBundle(
                    topic=research_dict["topic"],
                    category=research_dict["category"],
                    created_at=research_dict["created_at"],
                    sources=[ResearchSource(**item) for item in research_dict.get("sources", [])],
                    market_data=[
                        MarketSnapshot(**item) for item in research_dict.get("market_data", [])
                    ],
                    suggested_topics=research_dict.get("suggested_topics", []),
                    warnings=research_dict.get("warnings", []),
                )
                with st.spinner(
                    f"{settings.ai_provider.title()} is writing from the research evidence…"
                ):
                    draft_id, draft, quality = generate_and_save_draft(
                        topic=bundle.topic,
                        category=bundle.category,
                        tone=tone,
                        target_length=target_length,
                        research=bundle,
                        settings=settings,
                    )
                st.session_state.active_draft_id = draft_id
                st.session_state.draft_editor_value = draft
                st.success(f"Draft #{draft_id} saved. Review before using it anywhere.")
            except (WriterConfigurationError, WriterProviderError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(
                    f"Draft generation failed ({type(exc).__name__}). Check the logs and provider settings."
                )

    research_dict = st.session_state.research_bundle
    if research_dict:
        st.divider()
        st.subheader("Research results")
        for warning in research_dict.get("warnings", []):
            st.warning(warning)
        sources = research_dict.get("sources", [])
        if sources:
            st.caption(
                f"Topic: {research_dict.get('topic')} · Retrieved: {research_dict.get('created_at')}"
            )
            for idx, source in enumerate(sources, 1):
                with st.expander(
                    f"{idx}. {source['title']} · {source['publisher']}", expanded=(idx == 1)
                ):
                    st.markdown(f"[Open source]({source['url']})")
                    st.write(source.get("summary") or "No summary was supplied by the feed.")
                    st.caption(
                        f"Published: {source.get('published_at') or 'Not supplied'} · Retrieved: {source['retrieved_at']} · Relevance score: {source['relevance_score']}"
                    )
        else:
            suggestions = research_dict.get("suggested_topics", [])
            if suggestions:
                st.markdown("**Recent headlines that may help you choose a narrower topic:**")
                for suggestion in suggestions:
                    st.markdown(
                        f"- [{suggestion['title']}]({suggestion['url']}) — {suggestion['publisher']}"
                    )
        market = research_dict.get("market_data", [])
        if market:
            st.subheader("Public market snapshot")
            st.dataframe(
                [
                    {
                        "Symbol": item["symbol"],
                        "Last price (USDT)": item["price"],
                        "24h change (%)": item.get("price_change_percent_24h"),
                        "Retrieved at": item["retrieved_at"],
                    }
                    for item in market
                ],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Market figures are time-sensitive snapshots. Confirm the timestamp before reusing them."
            )

    if st.session_state.active_draft_id:
        draft_record = get_draft(settings.database_path, str(st.session_state.active_draft_id))
        if draft_record:
            st.divider()
            st.subheader(f"Draft editor · #{draft_record['id']}")
            with st.form(f"draft_form_{draft_record['id']}"):
                edited_text = st.text_area(
                    "Edit the draft",
                    value=st.session_state.draft_editor_value,
                    height=380,
                    key=f"draft_text_{draft_record['id']}",
                )
                save_clicked = st.form_submit_button(
                    "Save edits and rerun quality checks", type="primary"
                )
            if save_clicked:
                saved_research = ResearchBundle(
                    topic=draft_record["research"].get("topic", draft_record["topic"]),
                    category=draft_record["research"].get("category", draft_record["category"]),
                    created_at=draft_record["research"].get(
                        "created_at", draft_record["created_at"]
                    ),
                    sources=[
                        ResearchSource(**item)
                        for item in draft_record["research"].get("sources", [])
                    ],
                    market_data=[
                        MarketSnapshot(**item)
                        for item in draft_record["research"].get("market_data", [])
                    ],
                    suggested_topics=draft_record["research"].get("suggested_topics", []),
                    warnings=draft_record["research"].get("warnings", []),
                )
                report = check_content(edited_text, saved_research).to_dict()
                update_draft(
                    settings.database_path,
                    draft_record["id"],
                    draft_text=edited_text,
                    quality=report,
                )
                st.session_state.draft_editor_value = edited_text
                st.success(
                    "Edits saved and quality checks rerun. This draft is still not published."
                )
                st.rerun()
            latest = get_draft(settings.database_path, draft_record["id"])
            if latest:
                quality = latest["quality"]
                if quality["status"] == "passed":
                    st.success("Quality checks: passed")
                elif quality["status"] == "passed_with_warnings":
                    st.warning("Quality checks: passed with warnings")
                else:
                    st.error("Quality checks: failed")
                for warning in quality.get("warnings", []):
                    st.write(f"- {warning}")
                with st.expander("Show individual checks"):
                    st.json(quality.get("checks", []))

    st.divider()
    st.subheader("Saved draft history")
    drafts = list_drafts(settings.database_path, limit=25)
    if not drafts:
        st.info("No drafts saved yet. Run research and generate your first draft.")
    else:
        st.dataframe(
            [
                {
                    "ID": d["id"],
                    "Topic": d["topic"],
                    "Category": d["category"],
                    "Status": d["status"],
                    "Quality": d["quality"].get("status", "unknown"),
                    "Created": d["created_at"],
                }
                for d in drafts
            ],
            use_container_width=True,
            hide_index=True,
        )
        labels = {f"#{d['id']} · {d['topic']} · {d['created_at']}": d["id"] for d in drafts}
        selected_label = st.selectbox("Open a saved draft", ["Choose a draft…", *labels.keys()])
        if selected_label != "Choose a draft…" and st.button("Load selected draft"):
            selected_id = labels[selected_label]
            record = get_draft(settings.database_path, str(selected_id))
            if record:
                st.session_state.active_draft_id = selected_id
                st.session_state.draft_editor_value = record["draft_text"]
                st.rerun()

    st.caption(
        "Milestone 1 only: this application researches and drafts content. It does not generate images, auto-schedule jobs, or publish to Binance Square yet."
    )


st.set_page_config(
    page_title="AI Crypto Content Studio",
    page_icon="🪙",
    layout="wide",
)

page = st.navigation(
    [
        st.Page(
            render_content_workspace,
            title="Content Workspace",
            icon=":material/edit_note:",
            default=True,
        )
    ],
    position="sidebar",
)
page.run()
