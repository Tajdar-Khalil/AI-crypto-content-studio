# PRD.md — AI-Powered Crypto Content Research and Publishing Workflow

## 1. Document Overview

| Field | Details |
|---|---|
| Product name | AI Crypto Content Studio |
| Document type | Product Requirements Document |
| Version | 1.0 |
| Status | Draft — assumptions require validation |
| Product category | AI agents, financial content, workflow automation |
| Primary platform | Binance Square |
| Initial interface | Streamlit web dashboard |
| Primary language | English |
| Initial deployment | Single-user application |
| Initial account model | One owner's Binance Square account |

### 1.1 Product Vision

Build an AI-powered content workflow that researches cryptocurrency and financial topics, produces evidence-based posts, generates relevant images, checks content quality, and publishes approved posts to the owner's Binance Square account.

The product should reduce the manual effort required to research, write, illustrate, review, and publish useful financial content.

### 1.2 Product Principles

1. Accuracy is more important than publishing frequency.
2. Every time-sensitive factual claim should be supported by identifiable evidence.
3. AI-generated content must be reviewed before publication in the MVP.
4. Free or low-cost APIs should be preferred, subject to their current quotas and terms.
5. Publishing credentials must never be exposed to the browser or AI-generated content.
6. A failed API request must never be replaced silently with fabricated data or a dummy response.
7. The system must distinguish educational information, reported facts, analytical interpretations, and speculation.

## 2. Problem Statement

Creating high-quality cryptocurrency and financial content requires recurring research, source verification, writing, visual design, proofreading, and publishing.

Performing these activities manually is time-consuming and can lead to inconsistent quality, delayed publication, repetitive content, and factual errors.

Existing general-purpose AI chat interfaces can assist with writing, but a reliable content operation requires an integrated workflow that connects research sources, language models, image-generation services, quality checks, and the publishing account.

### 2.1 Problem to Solve

Provide one application where the owner can initiate or schedule a content workflow and manage the resulting content from research through publication.

The system must:

- Find relevant financial and cryptocurrency topics.
- Collect recent source material and market data.
- Produce original, readable content.
- Generate a matching visual asset.
- Check factual support and content quality.
- Allow the owner to edit and approve the result.
- Publish approved content to Binance Square through a supported publishing integration.
- Maintain a record of generated drafts and publishing attempts.

### 2.2 Value Proposition

**One workflow transforms verified financial information into reviewed, visually supported Binance Square content with less manual effort.**

The product's value is operational efficiency and consistent content quality, not a guarantee of audience growth, investment performance, or engagement.

## 3. Target Users

### 3.1 Primary User

An individual Binance Square creator interested in cryptocurrency, finance, blockchain technology, and financial education who wants to streamline content production.

Characteristics:

- Has an existing Binance Square account or can create one.
- Wants to publish informative content consistently.
- May have limited programming or AI integration experience.
- Prefers a visual dashboard over a command-line-only workflow.
- Wants control over what is published under their identity.

### 3.2 Secondary User — Future Scope

A content creator or small team managing financial content for multiple accounts.

Multi-user registration, separate customer workspaces, organization roles, billing, and support operations are not required for the MVP.

## 4. Assumptions and Decisions Requiring Approval

The implementation must follow these assumptions unless the product owner approves a change.

| ID | Assumption or decision | MVP default | Approval status |
|---|---|---|---|
| A-01 | Account model | One owner and one Binance Square account | Assumption |
| A-02 | Publishing behavior | Generate automatically, publish only after manual approval | Assumption |
| A-03 | Content language | English | Assumption |
| A-04 | AI provider | Groq API as the working default; Gemini remains optional only if deliberately configured | Confirmed for current MVP |
| A-05 | Image provider | Cloudflare Workers AI or another configured image API with suitable free-tier access | Provisional |
| A-06 | Market data | Binance public market data and/or a configured cryptocurrency data provider | Provisional |
| A-07 | Persistence | SQLite for the initial local application | Assumption |
| A-08 | Initial hosting | Run locally or on a suitable single-user host | Assumption |
| A-09 | Content formats | The implemented Square integration publishes text only; generated charts and infographics remain downloadable | Confirmed for current MVP |
| A-10 | Research coverage | Configured official sources, RSS feeds, and supported market-data endpoints | Assumption |
| A-11 | Automatic scheduling | Local scheduler or another simple configured scheduler | Provisional |
| A-12 | Operating cost | Prefer free tiers; no assumption of unlimited free API usage | Requirement |

### 4.1 Decisions Requiring Product Owner Approval

Before implementation or production deployment, confirm:

1. Whether the workflow will remain single-user or eventually support multiple users and their individual accounts.
2. Whether the first release must publish images directly to Binance Square, or whether generating and reviewing images is sufficient until the supported publishing capability is verified.
3. Whether publication should remain manually approved permanently or whether automatic publishing may be introduced in a later release.

The developer must document integration limitations discovered during implementation rather than inventing unsupported functionality.

## 5. Core User Journeys

### 5.1 First-Time Setup

1. The owner opens the application.
2. The owner configures the text-generation provider and its API credentials.
3. The owner configures the image-generation provider and its credentials.
4. The owner configures supported research sources and market-data access.
5. The owner configures the Binance Square publishing credential.
6. The system validates configuration where supported.
7. The dashboard displays the readiness status of each integration.
8. The owner can proceed with available features and sees actionable errors for incomplete configuration.

**Acceptance criteria:**

- No secret is displayed in full after it has been saved.
- An unavailable integration is clearly marked as disconnected or misconfigured.
- The workflow cannot attempt publication without valid publishing configuration.
- Missing optional market-data configuration does not prevent educational content from being created if an appropriate evidence source is available.

### 5.2 Create Content Manually

1. The owner opens the dashboard.
2. The owner selects a suggested topic or enters a topic manually.
3. The owner selects a content category and, where appropriate, a preferred writing style.
4. The research agent gathers available source material.
5. The research results are presented with their source URLs and relevant timestamps.
6. The writing agent generates a draft.
7. The image agent generates a relevant image when enabled.
8. The quality checks evaluate the draft and associated evidence.
9. The owner reviews and edits the output.
10. The owner approves, regenerates, or rejects the draft.
11. An approved draft can be submitted for publishing.

**Acceptance criteria:**

- The owner can inspect the sources used by the writer.
- A failed research request is not represented as successful research.
- The owner can edit the draft before publication.
- The system preserves the approved content for the publishing operation.
- Rejected content cannot be published accidentally.

### 5.3 Scheduled Content Generation

1. The owner enables the schedule and selects the frequency and preferred time.
2. The scheduler starts the workflow at the configured time.
3. The system selects an eligible topic.
4. Research, writing, image generation, and quality checks run in sequence.
5. A successful draft enters the pending-approval queue.
6. The dashboard shows the draft and its status.
7. Publication remains blocked until the owner approves the draft.

**Acceptance criteria:**

- Scheduled generation respects configured frequency and limits.
- Scheduled execution does not bypass human approval.
- Failed runs are logged and shown in the dashboard.
- The same scheduled run must not create duplicate drafts from repeated execution of the same job.

### 5.4 Approve and Publish

1. The owner opens a draft awaiting approval.
2. The owner reviews the content, evidence, image, and quality warnings.
3. The owner edits the draft if needed.
4. The owner explicitly approves publishing.
5. The system sends the approved content through the configured Binance publishing integration.
6. The system records the outcome and any post identifier or URL returned by the integration.

**Acceptance criteria:**

- Only an approved, publishable draft may be submitted.
- The publishing credential is used only by the backend publishing component.
- The system does not report success until the integration confirms success.
- If the result is uncertain, the draft is marked as requiring verification rather than being blindly submitted again.

### 5.5 Recover from a Failed Operation

1. An integration or workflow step fails.
2. The system records the failing step and an understandable error message.
3. Completed stages retain their available outputs.
4. The owner can retry the failed step where safe.
5. Retrying does not silently regenerate or publish a different post.
6. The system checks the previous publishing outcome before retrying an uncertain publishing request, where verification is supported.

## 6. User Stories

| ID | User story | Priority |
|---|---|---|
| US-01 | As an owner, I want to configure the AI providers so I can use my chosen services. | Must |
| US-02 | As an owner, I want current, sourced financial research so my posts are based on evidence. | Must |
| US-03 | As an owner, I want topic suggestions so I do not have to invent every topic manually. | Should |
| US-04 | As an owner, I want AI-generated posts so that content production takes less time. | Must |
| US-05 | As an owner, I want relevant generated images so my posts can include suitable visuals. | Must |
| US-06 | As an owner, I want factual and quality warnings before publishing. | Must |
| US-07 | As an owner, I want to edit, approve, reject, and regenerate drafts. | Must |
| US-08 | As an owner, I want to publish approved posts to my Binance Square account. | Must |
| US-09 | As an owner, I want to schedule draft generation so the workflow can run consistently. | Should |
| US-10 | As an owner, I want to review previous drafts and publishing results. | Must |
| US-11 | As an owner, I want understandable errors so I can fix integration problems. | Must |
| US-12 | As an owner, I want failed operations to preserve completed work. | Must |

## 7. Functional Requirements

Priorities are defined as Must, Should, and Could. All Must requirements are necessary for MVP acceptance.

### 7.1 Workflow Orchestration

**FR-001 — Workflow execution**  
The system must coordinate the workflow in this order:

1. Topic selection.
2. Research.
3. Writing.
4. Image generation, when enabled.
5. Quality checks.
6. Human review.
7. Publishing after approval.
8. Result logging.

**FR-002 — Stage tracking**  
The application must track the current stage and outcome of each workflow run.

**FR-003 — Error isolation**  
Failure at one stage must not erase successfully completed stages.

**FR-004 — Configurable provider usage**  
The workflow must use explicitly configured providers and must not silently substitute fabricated responses when a provider is unavailable.

**FR-005 — Usage controls**  
The system must avoid unnecessary repeated calls and respect configured provider limits where available.

### 7.2 Research Agent

**FR-006 — Topic research**  
The research agent must collect source material relevant to the selected finance or cryptocurrency topic.

**FR-007 — Source metadata**  
For each source used, the system must retain available metadata, including:

- Source title.
- Source URL.
- Publisher or domain.
- Publication timestamp, if available.
- Retrieval timestamp.
- Relevant extracted claims or summary.

**FR-008 — Source prioritization**  
The research agent should prioritize official project announcements, primary-source documentation, market-data providers, regulatory publications, and reputable financial reporting.

**FR-009 — Current-data verification**  
Time-sensitive claims must be evaluated against source timestamps. Market values must include their relevant retrieval time and currency or unit.

**FR-010 — Insufficient evidence**  
If research is unavailable or insufficient, the agent must flag the problem and must not manufacture factual claims to complete a draft.

**FR-011 — Research categories**  
The initial categories should include:

- Cryptocurrency education.
- Market and price analysis.
- Blockchain technology.
- Verified crypto news.
- Financial literacy.
- Cryptocurrency security and risk awareness.

The owner should be able to select a category for a manually initiated workflow.

### 7.3 Content Writing Agent

**FR-012 — Structured content generation**  
The writer must produce an editable draft with:

- Headline or opening hook.
- Main content.
- Key insights or supporting explanation.
- Conclusion or reader-engagement question, where appropriate.
- Relevant hashtags, where appropriate.
- Source references for material factual claims.

**FR-013 — Evidence-based writing**  
The writer must distinguish reported facts from analysis and speculation.

**FR-014 — Originality**  
The writer should produce original wording and avoid reproducing source articles verbatim.

**FR-015 — Style control**  
The writer must follow configured instructions for audience, tone, topic, and preferred post length.

**FR-016 — Financial safeguards**  
The writer must not present returns as guaranteed, fabricate statistics, invent quotations, or represent unsupported predictions as facts.

**FR-017 — Editable drafts**  
The owner must be able to edit generated content without losing the source material associated with the draft.

### 7.4 Image Generation Agent

**FR-018 — Image prompt generation**  
The system must prepare an image prompt based on the selected topic and generated content.

**FR-019 — API-based image creation**  
The system must generate an image through the configured image-generation provider when image generation is enabled.

**FR-020 — Image preview**  
The owner must be able to preview the generated image before publication.

**FR-021 — Regeneration**  
The owner must be able to request a replacement image when generation fails or the result is unsuitable.

**FR-022 — Image storage**  
Generated images must be stored or referenced reliably enough for preview and the subsequent publishing operation.

**FR-023 — Image-content consistency**  
The system should prevent an image from being attached to an unrelated or incompatible draft.

**FR-024 — Accurate numerical graphics**  
When a graphic contains factual prices, dates, or numerical statistics, those elements must be rendered from verified data rather than relying on the image model to reproduce exact text or figures.

**FR-025 — Publishing compatibility**  
Before implementation, verify whether the selected Binance Square integration supports the required image-posting workflow. If direct image posting is unavailable, retain the image for preview and download while allowing supported text-only publishing.

### 7.5 Fact-Checking and Quality Agent

**FR-026 — Claim review**  
The quality agent must compare material factual claims with the research evidence available to it.

**FR-027 — Source validation**  
The system should detect missing sources, inaccessible source URLs, stale information, contradictory claims, and unsupported numerical values where feasible.

**FR-028 — Content quality**  
The agent must check for incomplete content, obvious duplication, irrelevant hashtags, and unsupported certainty.

**FR-029 — Risk warnings**  
The system must flag misleading financial claims, guarantees of profit, unsupported price targets, fabricated breaking news, and potentially unsafe financial recommendations.

**FR-030 — Publishing eligibility**  
Each draft must have a quality outcome:

- Passed.
- Passed with warnings.
- Failed.

A failed draft must not be publishable without correction and a new quality check. Warnings must remain visible to the owner. The AI checker must not be presented as a guarantee of factual correctness or regulatory compliance.

### 7.6 Human Review and Approval

**FR-031 — Draft editor**  
The owner must be able to edit the title and post text before publication.

**FR-032 — Source inspection**  
The owner must be able to open the source URLs associated with the draft.

**FR-033 — Approval action**  
The owner must explicitly approve the final draft before a publishing request can be initiated.

**FR-034 — Rejection**  
The owner must be able to reject a draft and record an optional reason.

**FR-035 — Regeneration**  
The owner must be able to regenerate text or images while retaining the relevant topic and research where possible.

**FR-036 — Approval invalidation**  
If material content is changed after approval, the system must invalidate the previous approval and require another quality check and approval.

### 7.7 Binance Square Publishing

**FR-037 — Supported publishing integration**  
The system uses Binance's official Square posting script for text-only publication. Image attachments are not enabled in this application.

**FR-038 — Dedicated credentials**  
The system must use the supported dedicated publishing credential, not trading credentials or wallet secrets.

**FR-039 — Approved payload**  
The publisher must submit only the content approved for that publishing operation.

**FR-040 — Publication outcome**  
The system must record the actual result of each publishing request, including available post identifiers, URLs, timestamps, and errors.

**FR-041 — Duplicate prevention**  
The system must avoid unintended duplicate posts resulting from repeated clicks, repeated job execution, or automatic retries.

**FR-042 — Publishing status**  
The dashboard must distinguish at least:

- Not submitted.
- Publishing.
- Published.
- Failed.
- Outcome uncertain.

**FR-043 — Integration limits**  
The system must respect the publishing integration's currently documented payload requirements, authentication process, and rate limits.

**FR-044 — No trading functions**  
The application must not place trades, transfer funds, or request permission to perform account financial transactions.

### 7.8 Scheduling

**FR-045 — Enable and disable scheduling**  
The owner must be able to enable or disable scheduled workflow execution.

**FR-046 — Schedule settings**  
The owner must be able to select a time, frequency, and timezone.

**FR-047 — Manual execution**  
The owner must be able to start a workflow independently of the schedule.

**FR-048 — Approval enforcement**  
A scheduled workflow may generate and quality-check drafts, but it must not bypass manual approval in the MVP.

**FR-049 — Schedule visibility**  
The dashboard must show the next scheduled run and the last execution result when available.

### 7.9 History and Observability

**FR-050 — Draft history**  
The system must retain previous drafts and their statuses.

**FR-051 — Run history**  
The system must record workflow start time, end time, completed stages, and failures.

**FR-052 — Publishing history**  
The system must show previous publication attempts and their outcomes.

**FR-053 — Safe diagnostics**  
Logs must help diagnose errors without exposing API keys, access tokens, or other secrets.

## 8. Pages and Screens

### 8.1 Dashboard

**Purpose:** Provide an overview of current workflow activity.

Must display:

- Integration connection status.
- Number of drafts awaiting approval.
- Recent workflow results.
- Upcoming scheduled run.
- Recent publishing outcomes.
- Actions to create a post or review pending drafts.

### 8.2 Create Content

**Purpose:** Start a manual workflow.

Inputs:

- Topic or topic-selection option.
- Content category.
- Optional instructions or angle.
- Writing style or audience preference where configured.
- Image-generation enabled or disabled.

Actions:

- Start research.
- Generate content.
- View workflow progress.

### 8.3 Research Results

**Purpose:** Show the material used to create the post.

Must display:

- Topic summary.
- Retrieved source list.
- Source URLs.
- Available publication and retrieval timestamps.
- Relevant extracted evidence.
- Research warnings and errors.

### 8.4 Draft Editor and Preview

**Purpose:** Review and revise the generated post.

Must display:

- Editable content.
- Generated headline or opening.
- Hashtags, where appropriate.
- Generated image preview.
- Associated source references.
- Quality outcome and warnings.

Actions:

- Edit.
- Regenerate text.
- Regenerate image.
- Run quality check.
- Approve for publishing.
- Reject draft.

### 8.5 Approval Queue

**Purpose:** Show drafts awaiting owner review.

Must display:

- Draft title or topic.
- Creation time.
- Current quality status.
- Pending approval status.
- Link to the draft editor.

### 8.6 Publishing History

**Purpose:** Show previous publication operations.

Must display:

- Post topic or title.
- Submission timestamp.
- Publication status.
- Returned post URL or identifier, when available.
- Error details when publication failed.

### 8.7 Settings and Integrations

**Purpose:** Configure AI services, publishing, research, and scheduling.

Sections:

- Text AI provider.
- Image-generation provider.
- Market-data provider.
- Research sources.
- Binance Square publishing credentials.
- Schedule and timezone.
- Basic generation settings.

Secrets must be masked and must not be returned to the browser in full.

### 8.8 Workflow Logs

**Purpose:** Help the owner understand and recover from failures.

Must display:

- Workflow ID.
- Execution time.
- Stage name.
- Success or failure status.
- Safe error message.
- Retry action when the retry is supported and safe.

A separate administrative console is not required for the single-user MVP.

## 9. Roles and Permissions

### 9.1 MVP Role

The application has one role: **Owner**.

| Capability | Owner |
|---|---|
| Configure integrations | Allowed |
| Create content | Allowed |
| Run research and generation | Allowed |
| View sources and quality warnings | Allowed |
| Edit and regenerate drafts | Allowed |
| Approve or reject drafts | Allowed |
| Publish approved drafts | Allowed |
| Configure scheduling | Allowed |
| Review history and errors | Allowed |
| Manage publishing credentials | Allowed |

### 9.2 Future Multi-User Roles

Not part of the MVP.

If multi-user support is approved later, the design must isolate each user's drafts, settings, publishing credentials, and publishing history. A user must never be able to publish to or access another user's account through an authorization or ownership error.

## 10. Data Requirements

### 10.1 Workflow Run

Store:

- Unique run ID.
- Trigger type: manual or scheduled.
- Start and completion timestamps.
- Selected topic and category.
- Overall status.
- Current stage.
- Safe error information.
- Reference to the resulting draft.

### 10.2 Research Source

Store:

- Unique source ID.
- Associated workflow or draft ID.
- Title.
- URL.
- Domain or publisher.
- Publication timestamp, where available.
- Retrieval timestamp.
- Extracted evidence or summary.
- Source validation status.

### 10.3 Content Draft

Store:

- Unique draft ID.
- Topic and category.
- Headline or opening.
- Post body.
- Hashtags.
- Research references.
- Generated image reference, if available.
- Quality outcome and warnings.
- Draft status.
- Creation and last-modified timestamps.
- Approval status and approval timestamp.
- Approved content version.

### 10.4 Generated Image

Store:

- Unique image ID.
- Associated draft ID.
- Provider and model identifier.
- Image prompt.
- Storage reference or local path.
- Image format and dimensions, where available.
- Generation timestamp.
- Generation status.
- Publishing compatibility status, where applicable.

### 10.5 Publishing Record

Store:

- Unique publishing operation ID.
- Associated draft ID.
- Approved content version.
- Target platform.
- Submission timestamp.
- Outcome and status.
- Returned post ID or URL, where available.
- Safe error information.
- Attempt count.

### 10.6 Integration Configuration

Store:

- Provider type.
- Enabled or disabled state.
- Non-secret configuration.
- Secret reference or securely stored credential.
- Last validation result.
- Last successful connection time, where available.

Secrets must not be written into the source repository, ordinary logs, or frontend application state.

### 10.7 Schedule Configuration

Store:

- Schedule enabled state.
- Frequency.
- Preferred execution time.
- Timezone.
- Last execution.
- Next scheduled execution, where available.

### 10.8 Retention and Deletion

The MVP must allow the owner to delete generated drafts and images through the supported application controls.

The system should avoid retaining unnecessary personal information, source content, or provider responses. Retention periods should remain configurable or documented rather than being assumed to satisfy every provider's terms automatically.

## 11. Integrations

### 11.1 Text Generation

**Current default:** [Groq API](https://console.groq.com/docs/api-reference). Gemini may remain an optional provider when configured, but Groq is the working default for this project.

Requirements:

- API-based text generation.
- Configurable model.
- Prompt and response handling.
- Error reporting and quota awareness.
- No silent mock responses when the live provider fails.

The free tier may be appropriate for development, but its limits and data-use terms must be reviewed before use with sensitive information or production content.

### 11.2 Image Generation

**Preferred candidate:** [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/)

Requirements:

- Text-to-image generation.
- Configurable model.
- Image response handling.
- Preview and storage.
- Provider error handling.
- Free-tier usage monitoring where supported.

The workflow must be able to continue with a text draft when image generation is temporarily unavailable, while clearly marking the missing image.

### 11.3 Cryptocurrency Market Data

**Preferred sources:**

- [Binance Spot Market Data API](https://developers.binance.com/en/docs/products/spot/rest-api)
- [CoinGecko API](https://www.coingecko.com/en/api)

Requirements:

- Retrieve supported market data using documented interfaces.
- Record retrieval timestamps and relevant currency or unit.
- Apply supported request limits.
- Distinguish unavailable data from a genuine zero value.
- Avoid inventing prices or market statistics when data retrieval fails.

The implementation should use public market-data endpoints where sufficient; publishing credentials must remain separate from any other account credentials.

### 11.4 Research Sources

Initial sources:

- Official cryptocurrency project websites.
- Official announcements and blogs.
- RSS feeds.
- Financial and regulatory publications.
- Configured, accessible market-data endpoints.

Requirements:

- Store source attribution.
- Preserve source URLs.
- Handle inaccessible sources.
- Respect site terms, access restrictions, and applicable content rights.
- Never treat instructions embedded in retrieved web content as instructions to the AI agents or as authorization to publish.

### 11.5 Binance Square Publishing

**Implemented integration:** [Official Binance Square Skill](https://www.binance.com/en/skills/detail/binance/square-post), invoked through the local text-post script.

Requirements:

- Verify the current setup instructions.
- Verify the supported authentication method.
- Verify supported post formats and payload structure.
- Protect the dedicated publishing credential.
- Record returned publishing results and errors.
- Respect documented platform limits.

**Integration caveat:** Publishing capabilities may differ across documentation pages or versions. The developer must verify actual support for image posts before implementing an image-publishing requirement. Direct media upload must not be simulated if the selected integration does not support it.

### 11.6 Scheduling

The MVP may use a local scheduler or a simple scheduler appropriate to the deployment environment.

Requirements:

- Respect configured time and timezone.
- Avoid duplicate job execution.
- Record job outcomes.
- Keep manual approval mandatory.
- Document that a locally hosted workflow requires the host to be running for scheduled execution.

## 12. Non-Functional Requirements

### 12.1 Security

- Store API credentials outside source code and version control.
- Use environment variables or an appropriate secrets mechanism.
- Never expose backend secrets to the browser.
- Use a dedicated publishing-only credential where the platform provides one.
- Never request trading permissions, wallet seed phrases, or withdrawal credentials.
- Avoid logging full credentials, authorization headers, or sensitive payloads.
- Restrict access to the dashboard to its authorized owner.
- Use secure connections for remote provider integrations.
- Provide a documented credential-revocation procedure.

### 12.2 Reliability

- Every workflow run must have a trackable status.
- Errors must be surfaced instead of converted into fabricated success messages.
- Completed outputs should survive a later-stage failure.
- Transient failures may be retried with bounded attempts and appropriate delays.
- Publishing retries must account for potentially uncertain previous outcomes.
- A successful publishing result must be based on the actual integration response.

### 12.3 Performance

Initial targets for a normal single-user workflow:

- Dashboard should remain responsive while long-running jobs execute.
- Workflow progress should be visible during research, generation, and publishing.
- The interface should not freeze while waiting for an external AI service.
- Typical workflow completion time will depend on the number of sources, model response times, and image generation latency.

A strict end-to-end completion-time SLA is not required for the MVP.

### 12.4 Accuracy and Content Integrity

- Market figures must retain source and retrieval timestamps.
- Material facts should be traceable to supporting evidence.
- Unsupported numerical claims must be flagged.
- A quality-check pass is not a guarantee that every claim is correct.
- Financial content must not promise profits or imply guaranteed investment outcomes.
- The owner must retain control over publication.

### 12.5 Maintainability

- Keep research, writing, image generation, quality validation, scheduling, storage, and publishing as separate logical components.
- Use explicit interfaces between workflow stages.
- Make provider configuration separate from business logic.
- Keep error messages and integration logs understandable.
- Avoid unnecessary agent frameworks and infrastructure in the initial release.

### 12.6 Cost and Quota Management

- Prefer free tiers where suitable.
- Respect provider quotas and rate limits.
- Avoid repeated generation calls when existing outputs can be reused.
- Make quota or usage errors visible.
- Do not claim that third-party services will remain free.
- Require explicit configuration before introducing paid provider usage.

### 12.7 Compliance and Platform Integrity

- Follow the current Binance Square publishing rules.
- Do not create misleading financial claims, fake engagement, impersonation, or fabricated breaking news.
- Avoid duplicate or excessive automated posting.
- Respect third-party intellectual property and image-generation service terms.
- Review applicable requirements before expanding the product to additional users or jurisdictions.

## 13. Loading, Empty, and Error States

| Area | State | Expected behavior |
|---|---|---|
| Dashboard | Initial loading | Show a loading indicator while retrieving saved status and recent activity. |
| Dashboard | No activity | Explain that no workflows have run and provide a create-content action. |
| Integrations | Not configured | Mark the provider as disconnected and show setup instructions. |
| Integrations | Validating | Show a validation indicator and prevent duplicate validation submissions. |
| Integrations | Validation failed | Show a safe, actionable error without exposing credentials. |
| Research | In progress | Show the current research stage. |
| Research | No sources found | Explain that evidence was insufficient and prevent unsupported claims from being treated as verified. |
| Research | Partial failure | Retain usable source results and identify unavailable sources. |
| Writing | In progress | Show generation status and disable conflicting actions. |
| Writing | Generation failed | Preserve the research results and allow a safe retry. |
| Image generation | In progress | Show an image-generation indicator. |
| Image generation | Failed | Mark the image unavailable and allow text-only continuation where appropriate. |
| Quality check | Failed | Display the reason and block publishing until the failed checks are addressed. |
| Draft queue | Empty | Display a helpful empty state and an action to create content. |
| Approval | Content changed | Invalidate the previous approval and require a new review. |
| Publishing | In progress | Show that the publication request is being processed and prevent duplicate submission. |
| Publishing | Success | Show confirmed success and the returned post URL or identifier, when available. |
| Publishing | Failure | Show a safe error and allow retry when appropriate. |
| Publishing | Outcome uncertain | Require verification of the previous result before another publication attempt. |
| History | Empty | Explain that no prior activity has been recorded. |
| Scheduler | Disabled | Clearly show that automatic runs are disabled. |
| Scheduler | Job failed | Record the failure and show it in the workflow history. |
| Storage | Read/write error | Prevent misleading success states and explain that the result could not be saved. |

All loading states must terminate in a clear success, failure, or recoverable state wherever the application can determine the result.

## 14. MVP Scope

### 14.1 Included

The first release must include:

- A single-user dashboard.
- Integration settings.
- Manual topic selection and content generation.
- Research using a limited set of configured sources.
- Evidence and source tracking.
- AI-generated post drafts.
- AI-generated images using a configured API.
- Basic claim and content-quality checks.
- Draft editing and regeneration.
- Manual approval and rejection.
- Supported Binance Square publishing.
- Publishing status and history.
- Basic scheduled draft generation.
- Local persistent storage.
- Basic error handling and diagnostic logging.
- Credential protection and duplicate-publication safeguards.

### 14.2 Deferred or Out of Scope

The following are not required in the first release:

- Multi-user registration or a commercial SaaS subscription.
- Management of multiple Binance accounts.
- Fully autonomous publishing without human approval.
- Trading, portfolio management, or transaction execution.
- Automated financial advice or investment recommendations.
- Training custom language or image models.
- Fine-tuning large models.
- Paid, enterprise-grade data feeds.
- Complex research crawling across the entire internet.
- Engagement automation such as automated likes, comments, follows, or direct messages.
- Automated post editing, deletion, or account management.
- Advanced analytics and engagement prediction.
- Automatic selection of paid APIs.
- Mobile-native applications.
- Complex multi-agent frameworks or distributed orchestration infrastructure.

## 15. MVP Success Criteria

The MVP is successful when an owner can complete the entire supported process from topic selection to publication while retaining control over the final content.

| ID | Success criterion | Verification |
|---|---|---|
| SC-01 | A user can configure the required providers. | Validate each configured integration. |
| SC-02 | A workflow can collect source material for a selected topic. | Inspect recorded source URLs and retrieval metadata. |
| SC-03 | The writing agent produces an editable draft based on collected evidence. | Review the draft and associated sources. |
| SC-04 | The image agent can generate and display an image when enabled. | Verify generation and preview. |
| SC-05 | Quality checks identify missing evidence and configured risk conditions. | Test with valid, incomplete, and intentionally problematic drafts. |
| SC-06 | The owner can edit, reject, approve, and regenerate content. | Execute each action in the dashboard. |
| SC-07 | Unapproved content cannot be published. | Attempt to submit a draft without valid approval. |
| SC-08 | An approved post can be published through the verified integration. | Confirm the post in Binance Square and record the result. |
| SC-09 | Failed operations are visible and do not produce fabricated success messages. | Simulate missing credentials, quota errors, and provider failures. |
| SC-10 | A repeated publishing action does not knowingly create a duplicate post. | Test repeated submissions and uncertain outcomes. |
| SC-11 | Scheduled runs create drafts without bypassing approval. | Run a test schedule and confirm the draft remains pending review. |
| SC-12 | Previous runs and publishing outcomes can be reviewed. | Inspect saved history after successful and failed runs. |
| SC-13 | Secrets remain protected. | Inspect repository contents, logs, frontend responses, and configuration handling. |

### 15.1 Initial Operational Targets

These are proposed targets, not claims about existing performance:

- Generate at least one complete research-backed draft during a normal test run.
- Complete 10 consecutive end-to-end test workflows without an application-level crash.
- Ensure every confirmed successful publication has a corresponding local publishing record.
- Ensure failed or unverified operations are never falsely marked as published.
- Keep mandatory approval enabled for every publishing operation.
- Complete the core single-user workflow without manual database editing.

## 16. Acceptance Checklist

The product is ready for initial MVP use when:

- [ ] The application starts using documented setup instructions.
- [ ] Configuration and integration status are visible.
- [ ] Missing API keys are reported clearly.
- [ ] Research produces identifiable source references.
- [ ] Writing uses the research results.
- [ ] Image generation works with the configured provider.
- [ ] Failed API requests produce actionable errors.
- [ ] Drafts can be reviewed and edited.
- [ ] Material edits invalidate previous approval.
- [ ] Quality warnings are visible to the owner.
- [ ] Publishing is blocked until the final draft is approved.
- [ ] The supported Binance Square integration has been verified.
- [ ] Publishing results and errors are stored.
- [ ] Duplicate-publication safeguards are tested.
- [ ] Scheduling cannot bypass manual approval.
- [ ] API keys are not exposed in the frontend, logs, or source repository.
- [ ] The README explains installation, configuration, scheduling, limitations, and troubleshooting.

## 17. Implementation Guidance for the Coding Agent

Treat this document as the product source of truth.

1. Inspect the selected repository and existing application before changing the architecture.
2. Reuse existing working components where appropriate rather than replacing them without justification.
3. Implement the MVP incrementally, following the workflow order defined in this document.
4. Separate research, writing, image generation, quality checks, publishing, storage, and scheduling into maintainable components.
5. Verify external API authentication, payload formats, media support, quotas, and current platform behavior against official documentation.
6. Use real provider responses in production workflows. Mock services may be used only in isolated tests and must be clearly identified.
7. Do not implement unsupported publishing capabilities based on assumptions.
8. Never bypass credential protection or human approval to simplify implementation.
9. Add tests for workflow transitions, failure handling, and duplicate-publication safeguards.
10. Document any requirement that cannot be implemented because of provider or platform limitations, and propose the smallest reasonable alternative.
11. Keep the MVP focused on a functioning single-user workflow rather than prematurely implementing a multi-user SaaS architecture.
12. Update this PRD when an approved product decision changes the expected behavior.

## 18. Definition of Done

The MVP is done when the owner can configure the application, research a finance or cryptocurrency topic, generate an evidence-backed post and relevant image, review and edit the draft, pass its required quality checks, explicitly approve publication, publish through a verified Binance Square integration, and inspect the saved result.

The workflow must also handle missing credentials, provider failures, insufficient evidence, image-generation failures, and uncertain publication outcomes without inventing data, exposing secrets, or silently bypassing approval.

The system should be useful even when an optional integration is unavailable: completed research and drafts must be preserved, the failure must be visible, and the owner must be able to retry the affected stage safely.
