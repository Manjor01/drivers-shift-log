# Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Backend: Python 3.12, FastAPI, Pydantic v2 | Typed validation, OpenAPI for free |
| 2 | Database: SQLite (stdlib `sqlite3`) | Zero infrastructure, PK gives race-safe dedup |
| 3 | Frontend: React + TypeScript + Vite | Typed client, fast tooling |
| 4 | Tests: pytest + FastAPI TestClient; Vitest | Standard, fast |
| 5 | Quality: Ruff, mypy (strict), ESLint | Cheap, catches real bugs |
| 6 | CI: GitHub Actions (server, client, docker jobs) | Visible proof that checks pass |
| 7 | Docker Compose with backend + nginx-served frontend | One-command run for reviewers |
| 8 | No `GET /api/days` | Not required by the assignment |
| 9 | Single driver only (no `driver_id`) | Not required |
| 10 | Trip day = local date of `start` in `Asia/Almaty` | Deterministic; trips crossing midnight are not split |
| 11 | Timestamps stored as normalized UTC instants | Unambiguous, comparable |
| 12 | Money = integer KZT | No float rounding errors |
| 13 | `0 <= commission <= amount` | Rejects obviously invalid data |
| 14 | Trip identity = `id` | Client-generated key, as in the input data |
| 15 | POST: 201 created / 200 same normalized trip / 409 same id, different data | Safe retries, no silent overwrite |
| 16 | Empty day -> 200, zero summary, empty list | Empty is a valid state, not an error |
| 17 | Overlapping trips are not rejected | Not required by the assignment |
| 18 | No authentication | Out of scope |
| 19 | No Redis / PostgreSQL / Kafka / Kubernetes | Avoid overengineering |
| 20 | `net = revenue - commission` (totals and per payment method) | Assumption; the assignment does not define "на руки" further |
| 21 | Trips are loaded from `data/seed.json` through the same service layer as POST | One validation/dedup path |

## Step-0 tooling notes
- No API endpoints in Step 0, not even `/api/health`. Liveness is checked via FastAPI's built-in `/openapi.json`.
- Python dependencies are pinned by range only (no lockfile); the client uses `package-lock.json` + `npm ci`.
- ESLint 10 + `eslint-plugin-react-hooks` 7 (flat config). Earlier majors are deprecated or do not support ESLint 10.
- `jsdom` stays on 25: jsdom 30 requires Node >= 22.22.2, which would break tests for reviewers on slightly older Node 22. Its transitive `whatwg-encoding` deprecation warning during `npm install` is known and harmless.
- `pytest` runs with `filterwarnings = error`, so deprecation warnings fail the build.
- Production client: multi-stage build, `nginx-unprivileged` on :8080, `/api/` proxied to the backend.

## Plan
0. Foundation  1. Domain + validation  2. Summary + time utils  3. Storage  4. Idempotency  5. API + seed loading  6. Client  7. Polish

## Continuation after supplied archives (2026-10-07)

| # | Decision | Rationale |
|---|----------|-----------|
| 22 | Immutable Trip, equality across all normalized fields | Same ID with different content must be detectable |
| 23 | Maximum amount 1,000,000,000 KZT | Additional agreed input safety constraint, not an assignment requirement; it does not bound aggregate totals |
| 24 | ID matches `[A-Za-z0-9._:-]{1,64}` | Additional agreed identifier constraint |
| 25 | No maximum trip duration | The earlier proposed 24-hour rule was an unsupported business restriction |
| 26 | GET `/api/day?day=YYYY-MM-DD` returns summary and trips | The assignment defines behavior, not URL paths; one request keeps the UI consistent |
| 27 | POST accepts assignment names `start`, `end`, `payment` | Domain field names stay internal |
| 28 | SQLite stores normalized start and validated JSON payload | Minimal schema; fixed-width UTC start supports indexed day queries, JSON preserves every domain field |
| 29 | Seed loaded at application startup, through repository dedup path | Repeat startup is safe; conflicting data fails loudly |
| 30 | UI initially selects 2026-10-01 | Shows the supplied example immediately; user can select any other day |
| 31 | tzdata dependency | Named zones work even where the OS timezone database is absent |
| 32 | Writable SQLite Docker volume owned by app UID | Data survives container replacement; server runs as non-root |

The amount cap is a sanity bound on each trip. Python summary integers do not overflow at 64 bits, and the current SQLite schema does not store money in INTEGER columns. Do not describe the cap as complete protection from aggregate overflow.

| 33 | API day range 0002-01-01 through 9998-12-31, inclusive | Technical datetime bounds leave room for timezone conversion and next-day arithmetic; unsupported dates return 422 rather than 500 |
