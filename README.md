# AI Crypto Content Studio

A single-user Streamlit application that researches finance, cryptocurrency, trading, forex, spot/futures, and digital-asset technology topics; creates source-grounded posts; derives matching charts and infographics from the written post; validates the package; and provides a local approval and download flow.

Current implemented scope on the content-first workflow branch: niche-aware recent-topic suggestions from configured RSS feeds, RSS evidence collection, optional Binance Spot/Futures market data, Groq text generation (with optional Gemini support), selectable post formats, post-derived chart planning, Matplotlib charts, a template infographic, deterministic visual/quality checks, a one-time simpler-chart retry, draft editing, local approval and downloads, and SQLite history. Text-to-image generation, automatic scheduling, and Binance Square publishing are not implemented.

Requirements
- Python 3.11 or newer
- Internet access for configured RSS feeds and the selected AI provider
- Groq API key: https://console.groq.com/keys
Windows setup (PowerShell)
1. Open PowerShell in the project root.
2. Create and activate a virtual environment:
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
3. Install runtime and development dependencies:
   python -m pip install --upgrade pip
   pip install -r requirements-dev.txt
4. Create local configuration and edit it:
   Copy-Item .env.example .env
   notepad .env
5. Keep AI_PROVIDER=groq, set GROQ_API_KEY, and verify GROQ_MODEL against the current model list. Do not commit .env or share the key.
6. Start the dashboard:
   streamlit run app.py
Streamlit prints a local URL, normally http://localhost:8501.
Development checks
Format the source before checking it:
.\scripts\format.ps1
.\scripts\check.ps1
The check script runs syntax compilation, tests, Ruff linting, and Mypy. On macOS/Linux, run sh scripts/format.sh followed by sh scripts/check.sh.

If using Gemini instead of the working Groq default, install its optional SDK with pip install -r requirements-gemini.txt.
Configuration
All local environment variables are documented in .env.example.
Variable	Purpose	Default
AI_PROVIDER	Text provider (groq or optional gemini)	groq
GROQ_API_KEY	Groq API key	Empty until configured
GROQ_MODEL	Groq model available to the account	openai/gpt-oss-20b
GEMINI_API_KEY	Optional Gemini key	Empty
GEMINI_MODEL	Optional Gemini model	gemini-3.8-flash
DATABASE_PATH	SQLite database path	data/content_studio.db
MEDIA_STORAGE_PATH	Generated-image location for planned image support	data/generated_images
RSS_FEEDS	Comma-separated RSS/Atom feed URLs	CoinDesk, Cointelegraph, Decrypt, Bloomberg Markets, WSJ Markets, Google News forex search
RSS_TIMEOUT_SECONDS	RSS request timeout	12
REQUEST_TIMEOUT_SECONDS	General external request timeout	20
MAX_RESEARCH_RESULTS	Maximum relevant research sources	6
BINANCE_MARKET_DATA_ENABLED	Enable public market snapshots	true
LOG_LEVEL	Logging level	INFO


## Content-first multiagent workflow

1. Choose a niche: crypto market analysis, spot trading, futures/derivatives, forex/macro, finance and digital assets, blockchain technology, security/risk, or education.
2. Enter your own topic or discover recent, category-matched headlines from configured RSS feeds. These are recent feed suggestions, not social-platform trend metrics.
3. Research Agent collects directly relevant article titles, summaries, source URLs, dates/timestamps, and available public market snapshots. Review source coverage and warnings.
4. Content Writer receives the research bundle and writes the selected post format (market analysis, market update, news breakdown, explainer, beginner guide, thread, comparison, myth-vs-fact, checklist, trading concept, or technology explainer).
5. The visual planner reads the actual generated post. It creates a market chart only if the post mentions a supported asset and has market context; the original source-linked research remains available to support the visual. Unrelated technology/education posts get an infographic but no unrelated market chart.
6. The Chart/Plot Agent fetches validated Binance Spot or USDⓈ-M Futures candles for supported USDT pairs (BTC, ETH, BNB, SOL, XRP) and creates a suitable line, bar, candlestick, comparison, pie (selected-pair volume share), or scatter (observed price change vs quote volume) chart. A pie chart describes only the retrieved selected pairs, not whole-market share.
7. The infographic agent creates a template-based PNG summary from the post heading and key points. It is not a text-to-image model.
8. Visual and post quality checks are displayed. If chart retrieval or checks fail, the visual agent retries once using a simpler single-asset line chart; unresolved problems remain visible as warnings and no unvalidated chart is included.
9. Edit the post and regenerate its visual package, review the complete result, confirm approval, then download the Markdown post and available PNGs. The approval step is local; it does not publish content automatically.
10. Reopen saved drafts from local history. Rebuilt visuals are based on the saved post text.

The writer remains disabled when no directly relevant research sources are found. Suggested headlines help users choose a narrower research topic; they are not evidence for unrelated claims.

Market charts and data
- The Market charts and verified facts section retrieves historical Binance Spot and USDⓈ-M Futures candles for BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, and XRPUSDT.
- Supported periods are 24 hours, 7 days, and 30 days. Charts include line, per-candle percentage-change bars, candlesticks, and relative-performance comparison.
- The chart workspace uses pandas to validate and summarize returned OHLCV candles and Matplotlib to render PNG charts. It excludes the currently forming candle from historical period calculations.
- Futures views may include 24-hour change, volume, funding rate, mark price, index price, and open interest when Binance supplies those metrics.
- In the content-first workflow, market charts are generated downstream from the written post. The visual planner uses post context to select a chart and uses verified historical data and source timestamps rather than guessing values.
- These endpoints are public market-data endpoints. The application does not place trades or require private trading credentials. Futures data is market information, not a recommendation to trade.
- Market data cannot verify future prices. Any outlook must remain clearly labeled as uncertain. Gold pricing is deferred until a verified gold data source is selected.
Source documents
- PRD.md — product requirements and scope
- DESIGN.md — visual tokens, reusable UI patterns, responsive and accessibility rules
- ARCHITECTURE.md — application modules and integration boundaries
- DATABASE.md — SQLite schema, integrity, migration, backup, and recovery
- API.md — internal service contracts and external integrations
- AGENTS.md — coding and change discipline
Architecture
The MVP is a modular monolith. app.py is the Streamlit entry point and router. content_studio/ contains configuration, shared models, research, writing, quality checks, workflow orchestration, UI helpers, database setup, and repository functions. External HTTP requests belong in dedicated integration adapters as those integrations are implemented.

SQLite and generated media live under data/; local data and credentials are excluded from Git. Initialization is idempotent and includes a migration path for the original denormalized draft table.
Public APIs catalogue
https://github.com/public-apis/public-apis is a catalogue, not a universal API endpoint or key. Select an individual listing, read its official documentation, and integrate its specific authentication, terms, limits, and response format. For this project, use Groq for text generation, separate source feeds for research, and documented public market-data endpoints for market figures.
Current limitations
- RSS is a limited research source, not a full web-search engine.
- Topic matching is keyword-based and can miss relevant news.
- Quality checks do not guarantee factual accuracy or regulatory compliance.
- A text-to-image image-generation provider, automatic scheduling, and Binance Square publishing are not implemented. The infographic currently uses a template-based Matplotlib renderer.
- Free API tiers have quotas and may change.
- The application is intended for local single-owner use. Remote exposure requires an appropriate authentication layer and HTTPS.
Troubleshooting
- Groq HTTP 401: verify GROQ_API_KEY.
- Groq HTTP 403: check account status and model permissions.
- Groq HTTP 404: verify GROQ_MODEL against the current supported model list.
- Groq HTTP 429: check account usage and reset information in the Groq limits page.
- Groq HTTP 5xx or network timeout: retry when appropriate; saved research should remain available.
- RSS errors: check feed URL validity and network access.
- Database migration: back up the database and media folder before making manual schema changes.
Never paste API keys into screenshots or bug reports.