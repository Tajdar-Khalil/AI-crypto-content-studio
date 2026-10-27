# ARCHITECTURE.md — AI Crypto Content Studio

## 1. Purpose and Architecture Decision

Build a single-user, local-first Python application using a **modular monolith**. The app contains one Streamlit entry point, one SQLite database, local media storage, and dedicated adapters for external services. No microservices, task queues, Redis, vector database, or separate REST backend are required for the MVP.

`PRD.md` governs behavior; `DESIGN.md` governs UX; `DATABASE.md` governs persistence; `API.md` governs integration contracts; `AGENTS.md` governs implementation discipline.

## 2. Stack

| Concern | Choice | Reason |
|---|---|---|
| Runtime | Python 3.11+ | Data and AI ecosystem; compatible with current code |
| UI | Streamlit | Single-user dashboard without separate frontend stack |
| HTTP | `requests` | Simple REST integration |
| RSS parsing | `feedparser` | RSS/Atom parsing |
| Configuration | `python-dotenv` locally; Streamlit secrets/host secrets remotely | Keep secrets outside source code |
| Text AI | Groq API as current default; Gemini optional if deliberately configured | Preserve the working provider integration |
| Image AI | Cloudflare Workers AI or another verified image API, when implemented | External image inference |
| Persistence | SQLite via `sqlite3` | Appropriate for single-user low-write workloads |
| Testing | `pytest` | Unit and integration-mock testing |
| Lint/format | Ruff | Single tool for practical linting and formatting |
| Type checks | Mypy | Targeted static checks |
| Scheduling | OS/hosting scheduler invoking a Python command | Avoid background schedulers duplicated by Streamlit reruns |
| Deployment | Local first, suitable persistent single-user host later | Keep MVP operations simple |

## 3. Logical Architecture

```text
Owner
  -> Streamlit UI and navigation
  -> Application services
      -> Research agent -> RSS and public market data
      -> Writing agent -> Groq API
      -> Image agent -> configured image API (future phase)
      -> Quality agent -> deterministic checks, optional AI review
      -> Publishing service -> verified Binance Square integration (future phase)
      -> Repositories -> SQLite
      -> Media storage -> local generated-image files
```

All modules are in one deployable application. UI rendering must not contain raw provider requests. Agents must not query SQLite directly. Publishing is only invoked through the publishing service.

## 4. Project Structure

- `app.py`: Streamlit entry point and navigation.
- `content_studio/config.py`: configuration loading and validation.
- `content_studio/models.py`: shared typed data structures.
- `content_studio/database.py`: SQLite connection setup and schema migrations.
- `content_studio/repositories.py`: all persistence queries.
- `content_studio/workflow_service.py`: stage orchestration.
- `content_studio/draft_service.py`: draft revisions and approval eligibility when introduced.
- `content_studio/settings_service.py`: safe settings operations when required.
- `content_studio/scheduler.py`: due scheduled-run execution when implemented.
- `content_studio/research_agent.py`: source collection and evidence packaging.
- `content_studio/writer_agent.py`: post generation.
- `content_studio/image_agent.py`: image generation when implemented.
- `content_studio/quality_agent.py`: quality checks.
- `content_studio/publishing_service.py`: approved-version checks, explicit publish orchestration, duplicate prevention, and result handling for Binance Square.
- `content_studio/integrations/`: target location for provider-specific adapters as existing network calls are extracted in focused, tested refactors. In the current prototype, Groq calls are still in `writer_agent.py`, and RSS/market calls are still in `research_agent.py`; do not move these as part of unrelated setup changes.
- `content_studio/ui_components.py`: reusable presentation helpers.
- `tests/`: automated tests.
- `data/`: local database and generated media, excluded from Git except placeholders.

Only create a module when a current feature or well-defined architectural boundary needs it; do not add empty abstraction layers only for future possibilities.

## 5. Data Flow

1. Owner submits topic/category.
2. Workflow service records a run.
3. Research adapter retrieves source material and public market data.
4. Research evidence and timestamps are persisted.
5. Writer receives topic and evidence and calls Groq.
6. Draft is persisted as an immutable version.
7. Image generation runs if enabled and implemented.
8. Quality checks are persisted against the exact version.
9. Owner edits and reviews the draft.
10. An approved version can be submitted through the verified publisher.
11. Results and sanitized errors are persisted.

A later-stage failure must not erase completed research or generated text.

## 6. Database

Use SQLite with foreign keys enabled for every connection, parameterized SQL, transactions for related state transitions, UTC ISO-8601 timestamps, and explicit schema versions. Repositories own SQL queries; agents and UI do not write SQL directly. Generated image bytes live in the media directory; SQLite stores metadata and relative paths.

Preserve existing user data during migrations. If moving to a new schema, test migration against a copy before deployment. Do not use an ephemeral deployment filesystem for important drafts or images.

## 7. API and External Integrations

The MVP does not expose its own public REST API. Streamlit calls Python application services. Each external service has a dedicated adapter that owns authentication, request construction, timeouts, response parsing, provider errors, and retry behavior.

- Groq is the default text provider. Model names are configured, not scattered through code.
- RSS and official sources are untrusted evidence. Validate URLs, timestamps, and response sizes.
- Binance public market-data endpoints should be used when sufficient; market-data credentials are separate from publishing credentials.
- Image generation is independent of writing. Failure leaves the text draft intact.
- Binance publishing must use the verified official Square Skill or another explicitly approved supported interface. Text is the initial baseline; image posting is enabled only after verified support.

## 8. AI Agent Boundaries

Agents are ordinary Python modules, not autonomous processes. The workflow service decides execution order. The researcher collects evidence; the writer generates text from that evidence; the image agent creates media; the quality agent checks content; the publishing service enforces current-version approval. AI output is not proof of factual correctness.

Retrieved web content is untrusted and must not override system rules or authorize access to credentials or publishing.

## 9. Configuration and Secrets

Use `.env.example` as the documented local template; never commit `.env`. Hosted environments use platform secret storage. Required settings are validated before an integration is used. Do not put API keys or publishing credentials in SQLite `app_settings`, prompts, URLs, logs, or browser state. Bind local development to localhost. Remote hosting requires authentication, HTTPS, and persistent storage.

Expected settings include AI provider/model/key, RSS feeds and timeouts, market-data enablement, database path, media storage path, request timeout, and log level. Image/publishing settings are added when their adapters are implemented.

## 10. Errors and Reliability

- Use bounded retries for eligible transient failures only.
- Respect `Retry-After` and provider rate limits.
- Do not retry invalid credentials or invalid payloads until corrected.
- Preserve stage outputs when a downstream stage fails.
- Distinguish completed, failed, and uncertain publishing results.
- Do not claim a save succeeded if storage failed.
- Do not blindly retry a publishing operation with uncertain outcome.
- Sanitize logs and error messages to remove secrets.

## 11. Testing and Deployment

Use `pytest` and mocked HTTP responses for deterministic tests. Live integrations are opt-in and must not publish real posts automatically. Test workflow transitions, migrations, duplicate prevention, secrets redaction, API errors, and restore behavior. A local setup must document Python runtime, virtual environment, dependencies, `.env`, app startup, tests, scheduler, database, and media paths.

Use GitHub Actions only for safe tests and checks; CI must not receive production publishing credentials.

## 12. Future Scalability

Consider PostgreSQL, object storage, a task queue, a separate REST API, multi-user authentication, or a dedicated worker only when approved requirements or demonstrated operational constraints justify them. Future multi-user support requires explicit user ownership and data/credential isolation; it is not achieved by simply exposing the current shared workspace.
