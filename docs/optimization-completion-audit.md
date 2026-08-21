# Optimization completion audit

This audit maps the current optimization batch to implementation evidence and verification. It intentionally distinguishes completed application behavior from production infrastructure that must be supplied by a deployment environment.

| # | Improvement | Status | Implementation / verification evidence |
|---|---|---|---|
| 1 | Structured college recommendation facts | Complete | College results now expose structured facts separately from the AI explanation in `src/college_major.py`; rendered fact-card behavior is covered by frontend tests. |
| 2 | Visible source and data year | Complete | Each Scorecard metric carries its own latest available year, source URL, and retrieval date rather than presenting one misleading global year. |
| 3 | Editable and traceable filters | Complete | Explicit location, cost, admission-rate, size, degree, and program filters are normalized and returned with applied-filter trace information. |
| 4 | Honest major matching | Complete | Program matching distinguishes exact, related, and unverified CIP outcomes instead of treating every text similarity as an exact major match. |
| 5 | Actionable recommendation errors | Complete | Empty results, upstream-data failures, invalid filters, and generation interruptions have distinct user-facing recovery guidance. |
| 6 | Cached profile parsing | Complete | Profile document parsing is cached by file identity and modification state, avoiding repeated DOCX extraction. |
| 7 | Visible profile completeness | Complete | Missing action, challenge, outcome/impact, and reflection fields are represented consistently and feed the recommendation sufficiency check. |
| 8 | Manual profile additions | Complete | Users can add experience details through the profile information manager; additions are preserved separately from the read-only source profile. |
| 9 | Duplicate and conflict handling | Complete | Near-duplicate evidence is merged conservatively; likely contradictions require confirmation instead of silently overwriting source evidence. |
| 10 | Deterministic four-PIQ portfolio selection | Complete | `src/piq_portfolio.py` prioritizes individual quality, then reduces repeated experience, trait, and story type without allowing diversity to rescue weak choices. |
| 11 | High-value follow-up ordering | Complete | `src/piq_follow_up.py` ranks missing information by expected recommendation value and supports skipping one question or all remaining questions. |
| 12 | Versioned recommendation evaluations | Complete | Regression cases live under `backend/evals/` and are exercised by PIQ evidence, gap-ranking, portfolio, college-filter, and deterministic-ranking tests. |
| 13 | Server-side session/profile binding | Complete | Conversation state is bound to a profile and rejects profile mismatch; idle sessions are pruned with configurable TTL and capacity limits. |
| 14 | New-chat and profile-switch isolation | Complete | Starting a new chat and switching profiles no longer restores an unrelated previous conversation; verified in a real browser flow. |
| 15 | Responsive page scrolling | Complete | The document scrollbar reaches the bottom at mobile widths without a separate purple track or horizontal overflow; verified at 390x844. |
| 16 | Accessibility and interaction polish | Complete | Dialog semantics, focus trap/return, Escape close, keyboard behavior, and minimum touch-target sizing were added and browser-checked. |
| 17 | Bounded caches and performance safeguards | Complete | Profile localization/parsing caches and conversation storage are bounded; streaming retries and failures are tested. |
| 18 | Deployment quality boundary | Complete for this repository | Profile additions use an injectable repository with atomic JSON storage, CI runs backend and frontend quality gates, and deployment documentation states that production account authentication and a shared transactional data store remain host-environment responsibilities. |

## Official school information boundary

The application includes a deliberately limited registry of reviewed official university pages (`data/official_school_sources.json`) and validates HTTPS plus expected official domains before displaying them. The first reviewed adapter covers UCLA majors, first-year requirements, and tuition/fees. This avoids claiming that a brittle general-purpose crawler can reliably interpret every university website. Adding another institution is a controlled data-adapter task: supply reviewed official URLs, validate the domain, add tests, and record a review date.

## Verification snapshot

- Backend: 148 unit/integration tests passed.
- Frontend: 15 tests passed.
- Frontend production build passed.
- Frontend ESLint passed.
- `git diff --check` passed (line-ending conversion warnings only).
- Real-browser mobile and keyboard interaction checks passed; that check also exposed and led to a fix for the Send button forwarding a click event as message text.

## Production conditions that are not application code

Before serving unrelated real users from one deployment, the host must authenticate each account, derive profile ownership from that trusted identity, and configure a transactional repository implementation. A client-supplied profile identifier is intentionally not documented as proof of ownership.
