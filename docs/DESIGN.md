# DESIGN.md — AI Crypto Content Studio

## 1. Purpose

This document defines the visual and UX source of truth for the single-user Streamlit dashboard. `PRD.md` governs product behavior; `DESIGN.md` governs visual presentation and interaction. The interface must feel like a practical editorial and research workspace, not a generic AI SaaS landing page or trading terminal.

## 2. Design Principles

- Prioritize readable research, draft editing, evidence, and workflow status over decoration.
- Be honest about generated, checked, approved, and published states.
- Keep owner approval explicit before publication.
- Reuse shared components and styles.
- Show useful progress and actionable errors; never render fabricated success or data.
- Prefer a simple single-column layout, using two columns only where side-by-side editing and preview improve usability.
- Treat financial evidence, timestamps, quality warnings, and publishing outcomes as first-class information.

## 3. Visual Direction and Tokens

### Color palette

| Token | Value | Use |
|---|---|---|
| `color-background` | `#F5F6F8` | Main page background |
| `color-surface` | `#FFFFFF` | Primary content surfaces |
| `color-surface-subtle` | `#F0F2F5` | Secondary group backgrounds |
| `color-text-primary` | `#17212F` | Main text and headings |
| `color-text-secondary` | `#536174` | Supporting descriptions |
| `color-text-muted` | `#697586` | Metadata and timestamps |
| `color-border` | `#D9DEE7` | Dividers and borders |
| `color-border-strong` | `#AAB4C2` | Emphasized boundaries |
| `color-accent` | `#F0B90B` | Restrained amber accent |
| `color-primary-action` | `#243449` | Primary actions with white text |
| `color-primary-action-hover` | `#34465C` | Primary action hover |
| `color-success` | `#18794E` | Confirmed success |
| `color-success-surface` | `#EAF6EF` | Success background |
| `color-warning` | `#8A4B08` | Warnings |
| `color-warning-surface` | `#FFF4D6` | Warning background |
| `color-error` | `#B42318` | Errors and failed checks |
| `color-error-surface` | `#FDECEC` | Error background |
| `color-info` | `#175CD3` | Informational states |

Status colors must always be accompanied by text or an accessible label. Do not use amber as the background for white text if contrast is insufficient.

### Typography

Use Inter when available, otherwise a system sans-serif stack. Keep text readable and avoid decorative fonts.

| Style | Size | Use |
|---|---:|---|
| Page heading | 28 px | Page title |
| Section heading | 21 px | Major sections |
| Subsection heading | 17 px | Panels |
| Body | 14 px | General interface text |
| Draft preview | 16 px | Long-form content |
| Small metadata | 12 px | Timestamps and secondary details |
| Technical identifiers | 12–13 px | IDs and diagnostics |

Use sentence case. Avoid long uppercase labels and tiny helper text.

### Spacing and sizing

Use a 4 px spacing base: 4, 8, 12, 16, 20, 24, 32, 40, 48, and 64 px. Standard controls are approximately 40 px high; primary touch actions target 44 px. Standard panel padding is 16–20 px. Desktop page padding is 32 px, tablet 24 px, and mobile 16 px. Aim for a 1200 px main content maximum and a 240 px expanded sidebar where space permits.

Use 1 px borders, modest 4–12 px corner radii, and no default shadows. Do not wrap every group of text in a card.

## 4. Navigation and Page Structure

Planned navigation:

- Dashboard
- Create Content
- Approval Queue
- Publishing History
- Settings & Integrations
- Workflow Logs

The existing prototype may retain one functional Content Workspace route until additional pages are implemented. Do not show nonfunctional routes as available features without clear labeling.

Every page should have one title, a concise description where useful, and a clear primary action. Global navigation must highlight the active page and stay secondary to the content workspace.

## 5. Reusable Components

- **Primary button:** Main action for a page or workflow. Use one dominant primary action per context.
- **Secondary button:** Supporting actions such as Edit or View Sources.
- **Destructive button:** Delete or other consequential destructive action; confirm where data loss is meaningful.
- **Status label:** Consistent text labels and semantic color for pending, in progress, passed, warning, failed, published, and outcome uncertain.
- **Panel:** Group genuinely related content; avoid redundant nested cards.
- **Form field:** Visible label, appropriate helper text, inline validation, preserved values after recoverable errors.
- **Source item:** Title, publisher, source URL, publication time when available, retrieval time, summary, and validation status.
- **Workflow stage indicator:** Research, writing, image generation, quality check, review, publishing. Use not started, in progress, completed, failed, or skipped.
- **Draft editor:** Editable body, associated sources, image preview, quality findings, and appropriate save/regenerate/review actions.
- **Quality summary:** Overall outcome, passed checks, warnings, failures, and remediation guidance.
- **History table/list:** Clear headings, readable timestamps, status, and available identifiers/URLs.
- **Expandable details:** Suitable for long source excerpts and technical diagnostics, but never hide required approval warnings or uncertain publishing status.

## 6. Interaction and Feedback

- Use direct action labels such as “Research Topic”, “Generate Draft”, “Run Quality Check”, and “Approve for Publishing”.
- Disable conflicting controls while an operation is running and prevent duplicate submissions.
- Display the active workflow stage and finish with an honest success, warning, or error state.
- Use real progress when available. Do not invent percentages for operations with no progress telemetry.
- Preserve source data and completed outputs when a later stage fails.
- Material draft edits invalidate prior approval and require quality checks again.
- Publishing must not be triggered by generation completion or scheduling.
- If publication may have succeeded despite a timeout, show “Outcome uncertain” and verify before retrying.
- Prefer short 100–250 ms transitions only where they aid comprehension; respect reduced-motion settings where supported.

## 7. Loading, Empty, and Error States

| Context | Required behavior |
|---|---|
| Initial dashboard | Show loading state while data is retrieved |
| No activity | Explain there is no history and offer Create Content |
| Provider not configured | Show disconnected state and setup guidance |
| Research running | Show retrieval progress |
| No sources | Explain evidence is insufficient; do not imply research succeeded |
| Partial source failure | Preserve usable sources and list warnings |
| Writing running/failure | Show status; preserve research on failure |
| Image failure | Preserve text draft and allow text-only continuation |
| Quality failure | Explain why publication is blocked |
| Approval changed | Require new quality check and approval |
| Publishing success | Show confirmed status and returned post URL/ID if available |
| Publishing failure | Show sanitized error and safe retry guidance |
| Publishing uncertain | Prevent blind retry until result can be checked |
| Storage error | Never claim data was saved when it was not |

Every state must include an understandable message and, where useful, a next action.

## 8. Responsive Behavior

- Desktop (1024 px+): persistent sidebar where space allows; split editor/preview layout when useful.
- Tablet (768–1023 px): collapse navigation if the workspace is narrow; stack complex forms where needed.
- Mobile (below 768 px): 16 px side padding; stack editor, image, quality, and sources; use full-width primary buttons where appropriate; wrap long URLs and identifiers; avoid overflowing wide tables.

Draft editing, evidence inspection, quality warnings, approval, and publishing outcome must remain accessible on narrow screens.

## 9. Accessibility

Target WCAG 2.2 AA, subject to framework capabilities.

- Normal text contrast at least 4.5:1; large text at least 3:1.
- Use visible keyboard focus and logical tab order; no keyboard traps.
- All inputs have visible and programmatically associated labels.
- Icon-only controls require accessible names.
- State changes, errors, and success messages must be accessible to assistive technology where supported.
- Never communicate status through color alone.
- Do not make essential actions hover-only.
- Prefer touch targets around 44 × 44 CSS pixels for primary controls.
- Support zoom, text wrapping, and reduced motion where supported.

## 10. Streamlit Implementation

Use `.streamlit/config.toml` for the shared theme, with the palette above. Prefer native Streamlit widgets unless customization materially improves usability. Centralize CSS and avoid unstable internal framework selectors. Keep long-running work responsive and preserve draft/workflow state across reruns using persistent storage as the source of truth.

## 11. Acceptance Criteria

- Pages use consistent design tokens and component behavior.
- Important states are conveyed through text and not color alone.
- Research and draft sources remain inspectable.
- Empty and failure states explain the next useful step.
- Approval and publishing states are distinct and truthful.
- No fake metrics, market figures, or publishing results appear in the production UI.
- Keyboard, contrast, responsive, and form-label checks have been performed.
