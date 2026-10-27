"""Content-first Streamlit UI: research -> write -> visuals -> validation -> approval."""

from __future__ import annotations

import streamlit as st

from content_studio.config import get_settings
from content_studio.binance_square import publish_text_post
from content_studio.database import init_db
from content_studio.models import MarketSnapshot, ResearchBundle, ResearchSource
from content_studio.pipeline_service import generate_content_package
from content_studio.quality_agent import check_content
from content_studio.repositories import get_draft, list_drafts, update_draft
from content_studio.research_agent import collect_research
from content_studio.topic_agent import discover_topic_ideas
from content_studio.ui_components import render_page_header
from content_studio.visual_agent import generate_visual_package
from content_studio.writer_agent import WriterConfigurationError, WriterProviderError

NICHE_CATEGORIES = [
    "Crypto market analysis",
    "Spot trading",
    "Futures and derivatives",
    "Forex and macro markets",
    "Finance and digital assets",
    "Blockchain and digital-asset technology",
    "Crypto security and risk awareness",
    "Crypto education",
]
POST_FORMATS = [
    "Market analysis",
    "Short market update",
    "Recent news breakdown",
    "Educational explainer",
    "Beginner step-by-step guide",
    "Numbered thread",
    "Asset comparison",
    "Myth versus fact",
    "Practical checklist",
    "Trading concept explainer (risk-aware)",
    "Digital-asset technology explainer",
]


def _research_from_dict(value: dict) -> ResearchBundle:
    """Rebuild the typed research handoff saved in session state or SQLite."""
    return ResearchBundle(
        topic=value.get("topic", ""),
        category=value.get("category", ""),
        created_at=value.get("created_at", ""),
        sources=[ResearchSource(**item) for item in value.get("sources", [])],
        market_data=[MarketSnapshot(**item) for item in value.get("market_data", [])],
        suggested_topics=value.get("suggested_topics", []),
        warnings=value.get("warnings", []),
    )


def _reset_package_state() -> None:
    st.session_state.active_draft_id = None
    st.session_state.generated_post = ""
    st.session_state.post_quality = None
    st.session_state.visual_package = None

    # Local package approval
    st.session_state.package_approved = False
    st.session_state.approval_confirmation = False

    # Binance publishing safety
    st.session_state.publish_confirmation = False
    st.session_state.publish_attempted = False
    st.session_state.publish_result = None


def _render_research_evidence(research_data: dict) -> None:
    sources = research_data.get("sources", [])
    st.caption(
        f"Topic: {research_data.get('topic', '—')} · "
        f"Niche: {research_data.get('category', '—')} · "
        f"Retrieved: {research_data.get('created_at', '—')}"
    )
    for warning in research_data.get("warnings", []):
        st.warning(warning)

    if sources:
        st.success(f"Research agent collected {len(sources)} directly relevant source(s).")
        with st.expander("Inspect research sources and evidence", expanded=False):
            for index, source in enumerate(sources, start=1):
                with st.container():
                    st.markdown(f"**{index}. {source.get('title', 'Untitled source')}**")
                    st.caption(
                        f"{source.get('publisher', 'Unknown publisher')} · "
                        f"Published: {source.get('published_at') or 'Not supplied'} · "
                        f"Retrieved: {source.get('retrieved_at') or 'Not supplied'}"
                    )
                    st.markdown(f"[Open source]({source.get('url', '')})")
                    st.write(source.get("summary") or "No summary was supplied by the feed.")
                    st.divider()
    else:
        st.warning(
            "No directly relevant evidence was found. Topic suggestions may help you narrow the request, "
            "but a headline suggestion is not itself evidence for the topic."
        )
        suggestions = research_data.get("suggested_topics", [])
        if suggestions:
            with st.expander("Recent headlines from configured feeds"):
                for item in suggestions:
                    st.markdown(
                        f"- [{item.get('title', 'Untitled')}]({item.get('url', '')}) "
                        f"— {item.get('publisher', 'Unknown publisher')}"
                    )

    market_data = research_data.get("market_data", [])
    if market_data:
        st.markdown("**Market snapshots attached to research**")
        st.dataframe(
            [
                {
                    "Symbol": item["symbol"],
                    "Latest price": item["price"],
                    "24h change (%)": item.get("price_change_percent_24h"),
                    "Retrieved (UTC)": item.get("retrieved_at"),
                    "Source": item.get("source_url"),
                }
                for item in market_data
            ],
            use_container_width=True,
            hide_index=True,
        )


def _render_visual_package(visuals: dict, approved: bool) -> None:
    plan = visuals.get("plan", {})
    st.markdown("### Chart and plot agent")
    st.write(plan.get("reason", "The visual agent uses the written post to decide which data visuals are useful."))

    chart_png = visuals.get("chart_png")
    if chart_png:
        st.image(chart_png, caption=f"{plan.get('chart_type', 'Market').title()} chart · {', '.join(plan.get('symbols', []))}")
        if not approved:
            st.caption("Chart download unlocks after you approve the complete package.")
        else:
            st.caption("Use the chart download control in the final approval section below.")
    else:
        st.info(
            "No market chart was generated for this post, or live data could not be validated. "
            "The agent avoids creating an unrelated chart. Review the reason and warnings below."
        )

    snapshots = visuals.get("snapshots", [])
    if snapshots:
        st.markdown("**Market evidence used for the chart**")
        st.dataframe(
            [
                {
                    "Asset": item.get("symbol"),
                    "Market": str(item.get("market_type", "")).title(),
                    "Period": item.get("period"),
                    "Latest price (USDT)": item.get("price"),
                    "24h change (%)": item.get("price_change_percent_24h"),
                    "Period change (%)": item.get("period_change_percent"),
                    "Retrieved (UTC)": item.get("retrieved_at"),
                    "Source": item.get("source_url"),
                }
                for item in snapshots
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Infographic agent")
    infographic_png = visuals.get("infographic_png")
    if infographic_png:
        st.image(infographic_png, caption="Infographic summary derived from the generated post")
        st.caption(
            "This version uses a consistent Matplotlib layout and extracts key points from the written post. "
            "A text-to-image generation provider is not connected."
        )
        if not approved:
            st.caption("Infographic download unlocks after you approve the complete package.")
        else:
            st.caption("Use the infographic download control in the final approval section below.")
    else:
        st.warning("The infographic could not be rendered. The written post remains available for review.")

    validation = visuals.get("validation", {})
    if validation.get("status") == "passed":
        st.success("Visual validation passed.")
    elif validation.get("status") == "passed_with_warnings":
        st.warning("Visual generation completed with warnings; inspect them before approval.")
    else:
        st.error("Visual validation needs attention before you rely on the package.")

    with st.expander("Visual plan and validation checks", expanded=False):
        st.json({"plan": plan, "validation": validation})
    for warning in visuals.get("warnings", []):
        st.warning(warning)


def render_content_workspace() -> None:
    settings = get_settings()
    init_db(settings.database_path)

    defaults = {
        "research_bundle": None,
        "topic_suggestions": [],
        "topic_suggestion_warnings": [],
        "selected_topic_label": "Choose a recent topic idea…",
        "topic_mode": "Enter a topic",
        "active_draft_id": None,
        "generated_post": "",
        "post_quality": None,
        "visual_package": None,
        "generated_topic": "",
        "post_format_selected": "Educational explainer",
        "visual_market_preference": "spot",
        "visual_period_preference": "7d",
        "package_approved": False,
        "approval_confirmation": False,
        "publish_confirmation": False,
        "publish_attempted": False,
        "publish_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    render_page_header(
        "AI Crypto Content Studio",
        "A connected multiagent workflow: research first, write the post, create visuals from that post, validate, review, and approve.",
    )

    with st.sidebar:
        st.header("System status")
        if settings.text_ai_configured:
            st.success(
                f"Writing AI configured · {settings.ai_provider.title()} · {settings.selected_model}"
            )
        else:
            st.warning("Writing AI not configured")
            st.caption("Copy .env.example to .env, add GROQ_API_KEY, and restart Streamlit.")
        st.write(f"Research feeds: **{len(settings.rss_feeds)} configured**")
        st.write(
            f"Binance public market data: **{'Enabled' if settings.market_data_enabled else 'Disabled'}**"
        )
        st.write("Text-to-image provider: **Not connected**")
        st.write("Binance Square publishing: **Official script integration configured**")
        st.divider()
        st.markdown("**Agent path**")
        st.markdown(
            "1. Research & topic discovery\\n"
            "2. Content writer\\n"
            "3. Content-to-visual planner\\n"
            "4. Chart/plot + infographic agents\\n"
            "5. Validation and automatic retry\\n"
            "6. User approval, download, and optional confirmed publishing"
        )

    st.markdown("## 1 · Research and topic discovery")
    st.write(
        "Choose a niche, then research your own topic or discover recent headline ideas from the configured RSS feeds."
    )
    category = st.selectbox("Research niche", NICHE_CATEGORIES, key="research_category")

    discover_left, discover_right = st.columns([1, 1])
    with discover_left:
        if st.button("Discover recent topic ideas", use_container_width=True, key="discover_topics"):
            with st.spinner("Research agent is checking the configured news feeds…"):
                result = discover_topic_ideas(category, settings)
            st.session_state.topic_suggestions = result["topics"]
            st.session_state.topic_suggestion_warnings = result["warnings"]
            st.session_state.selected_topic_label = "Choose a recent topic idea…"
    with discover_right:
        st.caption(
            "Suggestions are recent feed headlines ranked for the selected niche. They are not social-media "
            "trend-volume measurements; live source coverage depends on RSS_FEEDS."
        )

    topic_mode = st.radio(
        "How would you like to start?",
        ["Enter a topic", "Use a recent topic idea"],
        horizontal=True,
        key="topic_mode",
    )
    effective_topic = ""
    if topic_mode == "Enter a topic":
        effective_topic = st.text_input(
            "Research topic",
            placeholder="e.g., Bitcoin weekly price movement, Ethereum scaling, forex and inflation",
            key="research_topic_input",
        ).strip()
    else:
        topics = st.session_state.topic_suggestions
        label_to_topic = {
            f"{item.get('title', 'Untitled')} — {item.get('publisher', 'Unknown publisher')}": item
            for item in topics
        }
        labels = ["Choose a recent topic idea…", *label_to_topic.keys()]
        selected_label = st.selectbox(
            "Recent topic ideas",
            labels,
            key="selected_topic_label",
        )
        if selected_label in label_to_topic:
            selected = label_to_topic[selected_label]
            effective_topic = selected.get("title", "")
            st.caption(
                f"Publisher: {selected.get('publisher', 'Unknown publisher')} · "
                f"Published: {selected.get('published_at') or 'date not supplied'}"
            )
            if selected.get("summary"):
                st.write(selected["summary"])
            if selected.get("url"):
                st.markdown(f"[Open headline]({selected['url']})")

    for warning in st.session_state.topic_suggestion_warnings:
        st.warning(warning)

    if st.button("Research this topic", type="primary", use_container_width=True, key="run_research"):
        if not effective_topic:
            st.error("Enter a topic or choose a recent topic idea first.")
        else:
            try:
                with st.spinner("Research agent is collecting relevant articles, timestamps, sources, and available market facts…"):
                    result = collect_research(effective_topic, category, settings)
                st.session_state.research_bundle = result.to_dict()
                _reset_package_state()
                st.session_state.generated_topic = effective_topic
                st.success("Research step completed. Review the evidence below before writing.")
            except Exception as exc:
                st.error(f"Research failed ({type(exc).__name__}). Check your network and RSS feed settings.")

    if st.session_state.research_bundle:
        _render_research_evidence(st.session_state.research_bundle)

    st.divider()
    st.markdown("## 2 · Content writer")
    research_data = st.session_state.research_bundle
    if not research_data:
        st.info("Complete the research step first. The writer receives the research result as its input.")
    else:
        st.caption(
            f"Writer input: research for “{research_data.get('topic', '')}” · "
            f"{len(research_data.get('sources', []))} directly relevant source(s)"
        )
    if not settings.text_ai_configured:
        st.warning(
            f"Add a valid API key for the configured provider ({settings.ai_provider}) to enable real writing. "
            "The application will not replace missing AI output with a dummy draft."
        )

    writer_col1, writer_col2 = st.columns(2)
    with writer_col1:
        post_format = st.selectbox("Post format", POST_FORMATS, key="post_format_selected")
        tone = st.selectbox(
            "Writing tone",
            [
                "Clear and educational",
                "Professional and analytical",
                "Beginner-friendly",
                "Concise and engaging",
            ],
            key="writer_tone",
        )
    with writer_col2:
        target_length = st.selectbox(
            "Target length",
            ["Short (100–180 words)", "Medium (180–300 words)", "Detailed (300–500 words)"],
            index=1,
            key="writer_target_length",
        )
        market_choice = st.selectbox(
            "Default market for matching charts",
            ["Auto-detect from post", "Spot", "Futures"],
            key="visual_market_choice",
        )
        period_choice = st.selectbox(
            "Default chart history",
            ["24h", "7d", "30d"],
            index=1,
            key="visual_period_choice",
        )
    preferred_market_type = "futures" if market_choice == "Futures" else "spot"
    research_bundle = _research_from_dict(research_data) if research_data else None
    can_generate = bool(
        research_bundle and research_bundle.sources and settings.text_ai_configured
    )

    if research_bundle and not research_bundle.sources:
        st.info(
            "Writing remains disabled because the research agent found no directly relevant evidence. "
            "Try a narrower topic or choose one of the recent headlines."
        )

    if st.button(
        "Generate post + matching visuals",
        type="primary",
        use_container_width=True,
        disabled=not can_generate,
        key="generate_content_package",
    ):
        try:
            with st.spinner(
                "Writer agent is drafting from the research. The visual planner will then read that exact post, "
                "create relevant data visuals, render an infographic, and validate the package…"
            ):
                package = generate_content_package(
                    topic=research_bundle.topic,
                    category=research_bundle.category,
                    tone=tone,
                    target_length=target_length,
                    post_format=post_format,
                    research=research_bundle,
                    settings=settings,
                    preferred_market_type=preferred_market_type,
                    visual_period=period_choice,
                )
            st.session_state.active_draft_id = package["draft_id"]
            st.session_state.generated_post = package["post_text"]
            st.session_state.post_quality = package["quality"]
            st.session_state.visual_package = package["visuals"]
            st.session_state.generated_topic = research_bundle.topic
            st.session_state.package_approved = False
            st.session_state.approval_confirmation = False
            st.session_state.publish_confirmation = False
            st.session_state.publish_attempted = False
            st.session_state.publish_result = None
            st.session_state.visual_market_preference = preferred_market_type
            st.session_state.visual_period_preference = period_choice
            st.session_state[f"post_editor_{package['draft_id']}"] = package["post_text"]
            st.success(
                f"Draft #{package['draft_id']} saved. The visual agent received the generated post as its input."
            )
        except (WriterConfigurationError, WriterProviderError, ValueError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Content pipeline failed ({type(exc).__name__}). Check provider settings and logs.")

    active_draft_id = st.session_state.active_draft_id
    if active_draft_id and st.session_state.generated_post:
        st.divider()
        st.markdown("## 3 · Review the connected content package")
        st.markdown("### Written post output")
        st.caption(
            f"Draft #{active_draft_id} · Format: {st.session_state.get('post_format_selected', 'Selected format')}"
        )
        editor_key = f"post_editor_{active_draft_id}"
        if editor_key not in st.session_state:
            st.session_state[editor_key] = st.session_state.generated_post

        with st.form(f"edit_post_form_{active_draft_id}"):
            edited_post = st.text_area(
                "Edit the post. Saving changes reruns the quality check and regenerates the matching visuals.",
                height=360,
                key=editor_key,
            )
            regenerate_clicked = st.form_submit_button(
                "Save edits and regenerate matching visuals",
                type="primary",
                use_container_width=True,
            )

        if regenerate_clicked:
            if not edited_post.strip():
                st.error("The post cannot be empty.")
            elif not st.session_state.research_bundle:
                st.error("The research bundle is missing. Run research again before regenerating visuals.")
            else:
                try:
                    current_research = _research_from_dict(st.session_state.research_bundle)
                    updated_quality = check_content(edited_post, current_research).to_dict()
                    update_draft(
                        settings.database_path,
                        active_draft_id,
                        draft_text=edited_post,
                        quality=updated_quality,
                    )
                    with st.spinner("Saving edits, refreshing the evidence check, and regenerating visuals from your edited post…"):
                        updated_visuals = generate_visual_package(
                            post_text=edited_post,
                            topic=st.session_state.generated_topic or current_research.topic,
                            research=current_research,
                            settings=settings,
                            preferred_market_type=st.session_state.visual_market_preference,
                            period=st.session_state.visual_period_preference,
                        )
                    st.session_state.generated_post = edited_post
                    st.session_state.post_quality = updated_quality
                    st.session_state.visual_package = updated_visuals
                    st.session_state.package_approved = False
                    st.session_state.approval_confirmation = False
                    st.session_state.publish_confirmation = False
                    st.session_state.publish_attempted = False
                    st.session_state.publish_result = None
                    st.success("Edits saved. The visual agent regenerated and rechecked the visuals from the edited post.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save and rebuild the package ({type(exc).__name__}).")

        quality = st.session_state.post_quality or {}
        quality_status = quality.get("status", "unknown")
        if quality_status == "passed":
            st.success("Post quality checks passed.")
        elif quality_status == "passed_with_warnings":
            st.warning("Post quality checks passed with warnings.")
        else:
            st.error(f"Post quality status: {quality_status}")
        for warning in quality.get("warnings", []):
            st.write(f"- {warning}")
        with st.expander("Post quality-check details", expanded=False):
            st.json(quality.get("checks", []))

        visuals = st.session_state.visual_package
        if visuals:
            _render_visual_package(visuals, bool(st.session_state.package_approved))

            st.markdown("### Final approval")
            st.checkbox(
                "I reviewed the post, chart decision, infographic, sources, and validation warnings.",
                key="approval_confirmation",
            )
            if st.button(
                "Approve this content package",
                type="primary",
                use_container_width=True,
                key="approve_package",
            ):
                if st.session_state.approval_confirmation:
                    st.session_state.package_approved = True
                    st.success("Package approved locally. Downloads are now available.")
                else:
                    st.warning("Tick the review confirmation before approving the package.")

            if st.session_state.package_approved:
                st.success("Approved package — ready to download.")
                st.download_button(
                    "Download written post (Markdown)",
                    data=st.session_state.generated_post,
                    file_name="approved_crypto_post.md",
                    mime="text/markdown",
                    key="download_package_post",
                )
                if visuals.get("chart_png"):
                    st.download_button(
                        "Download matching chart (PNG)",
                        data=visuals["chart_png"],
                        file_name=visuals.get("chart_filename") or "content_chart.png",
                        mime="image/png",
                        key="download_approved_chart",
                    )
                if visuals.get("infographic_png"):
                    st.download_button(
                        "Download infographic (PNG)",
                        data=visuals["infographic_png"],
                        file_name=visuals.get("infographic_filename") or "post_infographic.png",
                        mime="image/png",
                        key="download_approved_infographic",
                    )
                st.info(
                    "Your content package is approved locally. Publishing requires a separate "
                    "confirmation below. Review the exact post text before submitting it."
                )

                st.markdown("### Publish to Binance Square")
                st.warning(
                    "Publishing creates a real public post on your Binance Square account. "
                    "Check the content carefully before proceeding."
                )

                with st.expander("Review exact text to publish", expanded=True):
                    st.text(st.session_state.get("generated_post", ""))

                st.checkbox(
                    "I confirm that I want to publish this exact post to my Binance Square account.",
                    key="publish_confirmation",
                )

                publish_result = st.session_state.get("publish_result")
                if publish_result:
                    if publish_result.get("success"):
                        st.success("Binance Square reported a successful publishing operation.")
                        st.code(publish_result.get("message", ""))
                    else:
                        st.error("The publishing operation did not return a confirmed success.")
                        st.code(publish_result.get("message", "No details were returned."))

                        if publish_result.get("uncertain"):
                            st.warning(
                                "The result may be uncertain. Check your Binance Square profile "
                                "before attempting another submission. Do not retry automatically."
                            )

                if not st.session_state.get("publish_attempted", False):
                    if st.button(
                        "Publish approved post to Binance Square",
                        type="primary",
                        use_container_width=True,
                        key="publish_binance_square",
                        disabled=(
                            not st.session_state.get("publish_confirmation", False)
                            or not st.session_state.get("generated_post", "").strip()
                        ),
                    ):
                        # Set this before making the external request to reduce
                        # accidental duplicate submissions on ordinary reruns.
                        st.session_state.publish_attempted = True

                        with st.spinner("Submitting your approved post to Binance Square..."):
                            st.session_state.publish_result = publish_text_post(
                                st.session_state.get("generated_post", "")
                            )

                        st.rerun()
                else:
                    st.warning(
                        "A publishing attempt has already been made for this package. "
                        "Check Binance Square before considering another attempt."
                    )

    with st.expander("Saved draft history", expanded=False):
        drafts = list_drafts(settings.database_path, limit=25)
        if not drafts:
            st.info("No saved drafts yet. Run research and generate a content package.")
        else:
            st.dataframe(
                [
                    {
                        "ID": draft["id"],
                        "Topic": draft["topic"],
                        "Category": draft["category"],
                        "Status": draft["status"],
                        "Quality": draft["quality"].get("status", "unknown"),
                        "Created": draft["created_at"],
                    }
                    for draft in drafts
                ],
                use_container_width=True,
                hide_index=True,
            )
            labels = {
                f"#{draft['id']} · {draft['topic']} · {draft['created_at']}": draft["id"]
                for draft in drafts
            }
            selected_label = st.selectbox(
                "Open a saved draft",
                ["Choose a draft…", *labels.keys()],
                key="saved_draft_selection",
            )
            if selected_label != "Choose a draft…" and st.button("Load saved draft", key="load_saved_draft"):
                selected_id = labels[selected_label]
                record = get_draft(settings.database_path, str(selected_id))
                if record:
                    previous_id = st.session_state.active_draft_id
                    st.session_state.active_draft_id = selected_id
                    st.session_state.generated_post = record["draft_text"]
                    st.session_state.post_quality = record["quality"]
                    st.session_state.research_bundle = record["research"]
                    st.session_state.generated_topic = record["topic"]
                    if previous_id != selected_id:
                        st.session_state[f"post_editor_{selected_id}"] = record["draft_text"]
                    _bundle = _research_from_dict(record["research"])
                    with st.spinner("Rebuilding visuals from this saved post…"):
                        st.session_state.visual_package = generate_visual_package(
                            post_text=record["draft_text"],
                            topic=record["topic"],
                            research=_bundle,
                            settings=settings,
                            preferred_market_type=st.session_state.visual_market_preference,
                            period=st.session_state.visual_period_preference,
                        )
                    st.session_state.package_approved = False
                    st.session_state.approval_confirmation = False
                    st.session_state.publish_attempted = False
                    st.session_state.publish_result = None
                    st.rerun()

    st.caption(
        "Research and writing use configured sources and your selected AI provider. Market charts use validated public Binance "
        "Spot/Futures candles only when the written post justifies them. The infographic is a post-derived template graphic. "
        "No trades are placed. Binance Square publishing only runs after separate explicit confirmation."
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
            title="Content Studio",
            icon=":material/edit_note:",
            default=True,
        )
    ],
    position="sidebar",
)
page.run()
