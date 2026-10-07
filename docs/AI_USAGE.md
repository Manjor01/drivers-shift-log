# AI usage

This file is filled in during the work, not after. Only real cases are recorded.

## How AI was used
- Requirements analysis, ambiguity list and architecture proposal before any code (Claude).
- Step 0 scaffolding (Claude), verified by running the real tooling rather than trusting the generated files.

## AI mistakes and what I corrected

| Step | What the AI did wrong | How it was found | Fix |
|------|-----------------------|------------------|-----|
| 0 | First scaffold deviated from the approved scope: `requires-python >=3.11` instead of 3.12, no frontend, no Docker, no Vitest/ESLint. | Review against the approved decision list. | Rebuilt Step 0 to match the list exactly (3.12, client, Docker Compose, CI jobs). |
| 0 | Declared test dependency `httpx` from memory. Current Starlette (1.7) expects `httpx2` for `TestClient` and warns that `httpx` is deprecated. | `pytest` printed a deprecation warning that was easy to overlook. | Switched to `httpx2`, verified in a clean venv, added `filterwarnings = ["error"]` so warnings fail the build from now on. |
| 0 | Pinned `eslint ^9` and `eslint-plugin-react-hooks ^5` from memory. ESLint 9 is now in maintenance (npm printed "no longer supported"), and react-hooks 5 does not support ESLint 10, so a naive bump failed with `ERESOLVE`. | `npm install` deprecation warning, then the failed upgrade. | Moved to `eslint ^10`, `@eslint/js ^10`, `react-hooks ^7` (flat config API), clean reinstall, confirmed lint still fails on deliberately bad code. |
| 0 | Reported lint results with `${PIPESTATUS[0]}` in `/bin/sh`, which printed no exit code; an earlier `exit=0` actually belonged to `tail`. A silent `eslint .` was almost counted as a pass. | Noticed the "Bad substitution" error and the suspicious empty output. | Re-ran under `bash` with real exit codes and added sanity checks that the linters fail on known-bad input. |

## Not an AI error, but worth knowing
- Installing `node_modules` into the slow output mount hung the sandbox twice. Dependencies are now installed on the local disk.

## Continuation with Codex — 2026-10-07

The supplied project archive contained Step 0 only, despite its `step0_1` filename. A second archive held Step 1 tests, including the obsolete 24-hour restriction. Codex inspected the files rather than treating the earlier AI report as evidence, restored Trip from the approved contract, removed the unsupported restriction, and verified 103 tests.

The original assignment was requested and supplied before implementing the HTTP contract. Work continued with summary/time helpers, SQLite, idempotent POST, JSON seed loading, React UI, and documentation. The feature tests were written before these modules and failed on the missing storage module (collection-level RED, not assertion-level RED). Implementation then passed the tests. No claim is made that every UI test followed a RED/GREEN sequence.

### Actual corrections during continuation

- A first implementation called state setters synchronously inside a React effect. ESLint `react-hooks/set-state-in-effect` rejected it. Resetting the loading state was moved to user actions (date changes, reload, add), while the effect performs the fetch and cancels obsolete requests.
- The scaffold's frontend test expected the old English heading. It was replaced with tests for actual behavior: fetched summary, switching dates, empty state, and network error/retry.
- The proposed 24-hour rule remained in the supplied tests. It was replaced with a multi-day validity test, following the user's earlier decision.
- The Pydantic computed property worked at runtime but mypy rejected the decorator combination. A targeted `prop-decorator` ignore was added for the documented computed-property pattern; strict mypy remained enabled for the rest of the application.

These corrections were made collaboratively with AI and automated tools. They should not be presented as manually authored fixes by the applicant.

- The timezone configuration test exposed `IsADirectoryError` for `APP_TZ=America` when tzdata falls back to package resources. That exception is now converted to the same clear ValueError as other invalid zone names.
- During temporary mutation checks, same-size changes restored within one second left a stale Python bytecode cache. The checks were rerun with bytecode caches cleared and bytecode writing disabled, and each failure was checked for the intended assertion. The restored source then passed the full suite.

## Post-publication review correction

Codex reproduced HTTP 500 for day queries 0001-01-01 and 9999-12-31. The earlier tests covered typical days but missed datetime representational limits. An explicit supported date range was added to the query schema, documented, and tested for HTTP 422 on excluded dates and HTTP 200 at supported boundaries.
