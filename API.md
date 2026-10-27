# API.md — AI Crypto Content Studio

## 1. Communication Model

The MVP does not expose a public REST API. Streamlit calls Python application services directly; those services use agents, adapters, and repository functions. External API calls must remain inside dedicated adapters. All external credentials stay on the backend.

Internal operations include create workflow, collect research, generate draft, generate image when enabled, run quality check, edit draft, approve/reject, publish approved version, read histories, validate integration, and update non-secret settings. These are Python service operations, not HTTP endpoints.

## 2. Common Contracts

Validate required inputs and identifiers before performing work. Internal results should consistently convey success, data, error, warnings, and status. Application errors use a stable error category, safe message, failed stage, retryability, operation ID, and sanitized diagnostics when useful.

Use UUID identifiers for workflows, drafts, images, and publishing attempts. A client-provided identifier does not prove record ownership or authorization. Validate that a requested version belongs to the requested draft.

## 3. Authentication and Authorization

The MVP is single-owner. Local development binds to localhost. Remote access requires HTTPS and a verified authentication/access-control layer. Streamlit session state is not an authorization boundary.

Provider authentication:

- Groq: Bearer API key.
- Cloudflare Workers AI: Bearer API token and account identifier, when configured.
- Public Binance market data: no private key for documented public endpoints.
- CoinGecko: credential according to configured plan, if enabled.
- RSS: normally public GET access, subject to source requirements.
- Binance Square publishing: supported dedicated posting credential through the verified official Skill.

Never expose saved credentials in the browser, URL, prompts, logs, database settings, or error messages.

## 4. Groq Text Generation API

- Method: `POST`
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`
- Authentication: `Authorization: Bearer <GROQ_API_KEY>`
- Content type: JSON
- Model: configured using `GROQ_MODEL`
- Documentation: https://console.groq.com/docs/api-reference

Send a system instruction for source-grounded financial education and a user message containing the topic, tone, target length, and structured research evidence. Do not include secrets or unrelated personal data. Parse the documented response's `choices[0].message.content`, then validate it is non-empty before saving a draft.

Handle missing keys, authentication/permission failures, invalid models, HTTP 429, HTTP 5xx, timeouts, malformed response, and empty content distinctly. Use bounded retries only for retryable failures. Never substitute dummy content when the request fails.

## 5. Image Generation API

Proposed provider: Cloudflare Workers AI, subject to current model availability and account limits.

- Method: `POST`
- Endpoint pattern: `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}`
- Authentication: Bearer API token
- Documentation: https://developers.cloudflare.com/workers-ai/

The exact request/response format depends on the selected model. Validate returned image data and format, save it in application-controlled media storage, and associate it with a specific draft version. Text generation must remain usable if image generation fails. Do not imply image publishing is supported unless verified separately.

## 6. Research and Market Data

### RSS

Use `GET` against individually configured RSS/Atom URLs. Validate HTTP/HTTPS URLs, apply request timeouts and response-size limits, and parse using the configured RSS parser. Record title, link, publisher, publication timestamp when available, retrieval time, evidence summary, and status. Retrieved source content is untrusted input and must not override system instructions.

### Binance public market data

For a public ticker snapshot, use documented endpoint patterns such as `GET https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT`, when the endpoint meets the need. Documentation: https://developers.binance.com/en/docs/products/spot/rest-api and https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md.

Validate symbols and numeric values, preserve quote currency and retrieval time, and distinguish absent data from zero. Do not fabricate market figures when a request fails.

CoinGecko may be added as an optional data provider. Use the current official plan-specific authentication and endpoint documentation: https://docs.coingecko.com/.

## 7. Binance Square Publishing

The application currently uses the official Binance Square posting script from the Square Skill for text posts only. Its local adapter runs `scripts/binance-square/post-text.mjs` with Node.js 18+ and reads `BINANCE_SQUARE_OPENAPI_KEY` from the process environment. It never accepts trading or wallet credentials. The UI requires saved-version approval and a separate publish confirmation.

- https://www.binance.com/en/skills/detail/binance/square-post
- https://github.com/binance/binance-skills-hub/tree/main/skills/binance/square-post

The current local script publishes text and reports the post ID/link. Image publishing is not enabled in the application; generated charts and infographics are downloads. Keep the integration aligned to the official skill's current runtime and payload requirements.

The publishing service retrieves the approved version from persistent storage and constructs the payload server-side. Revalidate quality status, approval version, configuration, and active attempts immediately before submission. Persist a publishing-attempt record and record confirmed result IDs/URLs.

A timeout does not prove a post failed. Record uncertain outcomes and verify before retrying where possible. Local operation IDs help prevent duplicate local submissions but do not guarantee remote exactly-once delivery unless the provider supports idempotency.

## 8. Scheduling and Webhooks

The scheduler is a local or hosting job that calls application services; it is not a public endpoint. It generates pending drafts and never bypasses approval. No inbound webhooks are required for the MVP. If webhooks are introduced later, require documented signature verification, timestamp tolerance, replay protection, event deduplication, and safe payload validation.

## 9. Rate Limits and Retries

All requests need timeouts. Respect provider quotas, `Retry-After`, and documented request weights. Use bounded backoff for eligible transient failures. Do not repeatedly retry invalid credentials, unsupported models, invalid payloads, or permanent permission errors. Do not automatically retry uncertain publishing operations before verification.

## 10. History Queries

There are no public REST pagination endpoints. Internal history services should use bounded queries, default page size 25, maximum 100, and filters such as status, start/end time, and draft ID where useful. Prefer stable cursor pagination for changing lists. Do not invent pagination parameters for providers that do not support them.

## 11. Error Codes

Use consistent application error categories:

- `CONFIGURATION_ERROR`
- `AUTHENTICATION_ERROR`
- `PERMISSION_ERROR`
- `RATE_LIMITED`
- `PROVIDER_UNAVAILABLE`
- `NETWORK_TIMEOUT`
- `INVALID_RESPONSE`
- `INSUFFICIENT_EVIDENCE`
- `IMAGE_GENERATION_FAILED`
- `QUALITY_CHECK_FAILED`
- `APPROVAL_REQUIRED`
- `VERSION_MISMATCH`
- `DUPLICATE_OPERATION`
- `PUBLISHING_FAILED`
- `PUBLISHING_UNCERTAIN`
- `STORAGE_ERROR`

User-facing errors state what failed, what was preserved, and the safe next step. Never display secrets or raw authorization headers.

## 12. Configuration and Privacy

Required settings depend on enabled integrations and include `AI_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`, `DATABASE_PATH`, `MEDIA_STORAGE_PATH`, `REQUEST_TIMEOUT_SECONDS`, `LOG_LEVEL`, configured RSS feeds, and the market-data flag. Add image or publishing credentials only when those integrations are implemented. Local development uses `.env`; hosted deployment uses platform secrets. `.env` is never committed.

Send only needed evidence to AI providers. Do not send API keys, Binance posting credentials, wallet secrets, or unrelated private database content. Review provider terms, limits, and data-handling policies before production use.

## 13. Testing

Use mocked responses for normal tests. Live provider tests are opt-in, sanitize errors, and never publish a real post automatically. Test successful responses, missing keys, authentication failures, model errors, quotas, 5xx responses, timeouts, malformed data, duplicate attempts, approval enforcement, and uncertain publishing outcomes.
