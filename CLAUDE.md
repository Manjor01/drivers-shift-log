# Driver Shift Diary — project conventions for Claude Code

Take-home project: trip tracker for a driver. Server (FastAPI + SQLite) + web client (React + TS + Vite).
Source of truth for decisions: `docs/DECISIONS.md`. Do not change a decision silently — update that file in the same commit.

## Commands
- `make setup-server` / `make setup-client` — install dependencies
- `make lint` — ruff (check + format) + mypy for server, eslint + tsc for client
- `make test` — pytest for server, vitest for client
- `make up` — build and run everything with Docker Compose (UI on :8080, API on :8000)

## Hard rules
- Money is `int` (whole KZT). Never `float`. Reject non-integers and booleans.
- Datetimes must carry a UTC offset. Store as normalized UTC, return in `APP_TZ` (default `Asia/Almaty`).
- A trip belongs to the local day of its `start` in `APP_TZ`.
- Idempotency key is the trip `id`: created -> 201, same normalized trip -> 200, same id but different data -> 409.
- Duplicate protection relies on the PRIMARY KEY + `ON CONFLICT`, never on SELECT-then-INSERT.
- `compute_summary` is a pure function (no I/O) and is tested in isolation.
- All SQL is parameterized.

## Scope guards
- No auth, no overlap checks, no `GET /api/days`, no extra infrastructure (Redis, Postgres, queues, k8s).
- Single driver only.

## Workflow
- Work in small steps; one commit per step, tests included, CI green before moving on.
- Write the test list first, then the code. Do not shape tests around the implementation.
- Whenever AI-generated output turns out wrong and is corrected, add an entry to `docs/AI_USAGE.md`. Real cases only, never invented.
- Python: ruff + mypy strict, type hints everywhere. TypeScript: strict, no `any`.
- Report commands that were run and their real results; never claim a check passed without running it.
