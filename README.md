AI Crypto Content Studio
A single-user Streamlit workspace for researching finance and cryptocurrency topics, generating source-grounded drafts with Groq, checking basic content quality, and saving editable drafts locally in SQLite.
Current implemented scope: RSS-based research, optional public Binance market snapshots, Groq text generation (with optional Gemini support), basic deterministic quality checks, draft editing, SQLite history, and base Streamlit navigation. Image generation, scheduled execution, and Binance Square publishing are not implemented yet.

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
RSS_FEEDS	Comma-separated RSS/Atom feed URLs	CoinDesk, Cointelegraph, Decrypt
RSS_TIMEOUT_SECONDS	RSS request timeout	12
REQUEST_TIMEOUT_SECONDS	General external request timeout	20
MAX_RESEARCH_RESULTS	Maximum relevant research sources	6
BINANCE_MARKET_DATA_ENABLED	Enable public market snapshots	true
LOG_LEVEL	Logging level	INFO


Current workflow
1. Enter a focused finance or crypto topic.
2. Click Research topic to collect configured RSS evidence and optional public market data.
3. Inspect source URLs, summaries, timestamps, and warnings.
4. Generate a draft only when directly relevant sources are available and the selected text provider is configured.
5. Edit the draft and rerun basic quality checks.
6. Reopen saved drafts from local history.
The application refuses to draft from zero directly relevant research sources. Suggested headlines are prompts for narrowing a topic, not evidence for the requested claim.
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
- Image generation, automatic scheduling, and Binance Square publishing are planned but not implemented.
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