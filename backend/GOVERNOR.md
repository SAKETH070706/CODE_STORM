# PNG5 Agent Permission Governor

This implementation extends the working CODE_STORM backend. It does not start a server, modify your real `.env`, install dependencies, call live providers, migrate your existing database, or send email during verification.

## Inspection and stages

The baseline already implemented role bearer tokens, strict read arguments, role/task/resource checks, fixed parameterized reads, evaluation and execution endpoints, persistent action states, and SHA-256-linked SQLite audit events. The existing governor files and `api/main.py` were uncommitted when work began; their functionality was used as the baseline.

Missing or unsafe boundaries were role-wide record access, role-only task assignment, unimplemented report adapters, no approval or idempotency lifecycle, no risk/semantic integration, no crash reconciliation, wildcard CORS, unauthenticated knowledge administration, and treating retrieved text as verified instructions. Gemini combined system and user messages. No applicable AGENTS.md was found in the workspace or checked ancestors.

The implementation is grouped into four stages:

1. Identity and persistence: trusted principals, additive migration, ownership, task assignments, transactional audit writes, and a single-process lease.
2. Policy and context: strict tool schemas, explicit capabilities, artifact provenance/sensitivity, weighted risk and policy digest binding.
3. Execution and review: registered adapters, persistent review decisions, revalidation, atomic claims, idempotency, CSV/JSON reports and simulated outbox.
4. Semantic and operational hardening: strict raw JSON assessment, deadlines/concurrency limits, authenticated administration, body limits, checkpoint verification, tests and benchmarks.

## Architecture and trust boundary

`api/governor.py` authenticates via `governor_identity.py`, then calls `Governor`. Policy evaluation resolves an active `(principal_id, role, task_id)` assignment from SQLite. Client identity, role, provenance and arbitrary extra fields are rejected. Identifiers are exact and case-sensitive: no case-folding or whitespace changes that could alter meaning. Missing read limits normalize to 10; permitted report defaults are canonicalized before hashing.

The policy engine checks role/tool/resource and task allowlists before risk or semantics. The policy file contains weights and thresholds; the capability matrix remains code-controlled in `permission_governor.py`. Change the policy version when changing either. SQL, shell, path and financial execution capabilities simply do not exist. Unsupported argument fields, paths, SQL strings and destinations never become adapter inputs. Regex is not an execution sandbox. Discussion text is not scanned as though it were executable code by the governor; there is no free-text executable argument.

A read produces a server-owned data artifact. `report.create` requires its exact ID and task/owner/resource, writes a real report atomically under `backend/data/reports`, and records a SHA-256 digest and source artifact. CSV cells beginning with spreadsheet formula characters are escaped. `report.send` requires a server-created report and an allowed sensitivity and destination. It inserts a persistent outbox record and returns `delivery_mode="simulated"`. No network delivery occurs. The outbox primary key prevents duplicate entries for the same action.

The old `execute_authorized_read` import remains but rejects execution: an evaluation response is not a permit. Python code, SQLite files, policy files and report directories must be writable only by trusted operators. This is an API/tool boundary, not a sandbox for hostile Python running in the server process.

## Databases, migration and recovery

`core/governor_store.py` contains explicit migration version 1. It adds `schema_migrations`, `governed_actions`, `task_assignments`, `approvals`, `artifacts`, `idempotency` and `outbox`, while preserving the existing `actions` and `audit_events` tables and every historical event/hash. Startup never deletes history or repairs/rehashes it. Old actions without a trustworthy principal mapping are not exposed to agents; a reviewer with audit permission can inspect historical audit entries.

Governance uses SQLite WAL, `synchronous=FULL`, foreign keys and a 2-second busy timeout, with short `BEGIN IMMEDIATE` write transactions. State transitions and their audit events commit together. Expensive provider calls and report I/O do not hold the governance transaction. Business data uses a separate `mode=ro`, `query_only=ON` connection. Chroma remains a supporting policy-document retrieval store; it is not the governance database or business-data authorization source. Retrieval in the legacy process endpoint is explicitly untrusted and cannot grant tool authority.

One process per database is enforced with an OS file lease. Use one Uvicorn worker. Threads can handle concurrent requests; state claims serialize through SQLite. Startup checks audit integrity and marks interrupted nonterminal execution attempts `OUTCOME_UNKNOWN`; it never blindly replays them. Pending reviews survive restart. Reconcile uncertain actions with artifact/outbox records and audit before issuing a new action/key. Do not delete the lease file while a server is running.

## Identity and local setup

From the repository root in PowerShell, use an existing environment or install locally yourself:

```powershell
# Optional; not run by the implementation agent:
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

# Generate three different tokens, then set them in backend/.env or your shell.
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$env:GOVERNOR_ANALYST_TOKEN = '<first generated token>'
$env:GOVERNOR_SUPPORT_TOKEN = '<second generated token>'
$env:GOVERNOR_REVIEWER_TOKEN = '<third generated token>'
$env:GOVERNOR_REVIEWER_PERMISSIONS = 'review,audit,knowledge_admin'
$env:CORS_ORIGINS = 'http://localhost:5173'

Push-Location backend
..\.venv\Scripts\python.exe -m core.governor_store
..\.venv\Scripts\python.exe -m core.demo_data
..\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1 --limit-concurrency 64 --timeout-keep-alive 5
Pop-Location
```

Use the actual generated values rather than the bracketed placeholders. Startup requires three unique ASCII tokens of at least 32 characters. Token comparisons are constant-time; tokens are not stored in governance records. Demo identities are `analyst-1`, `support-1`, `reviewer-1`; seeded assignments are `sales-report` and `support-review` for the corresponding agents. The reviewer has only explicitly configured permissions. Remove `knowledge_admin` or `audit` when not needed. Creating additional identities requires trusted server configuration and an individual task assignment; clients cannot self-assign.

`httpx>=0.27.0` is the only added dependency, for API tests. Production execution uses the existing stack and built-in sqlite3. Dependency installation and real-database migration were **not run**. Keep a consistent SQLite backup before deployment; do not copy just the main file while WAL writes are active.

## Copy-paste API walkthrough

In a second PowerShell window, set the same three token environment variables. Then:

```powershell
$base = 'http://127.0.0.1:8000'
$analyst = @{Authorization="Bearer $env:GOVERNOR_ANALYST_TOKEN"}
$support = @{Authorization="Bearer $env:GOVERNOR_SUPPORT_TOKEN"}
$reviewer = @{Authorization="Bearer $env:GOVERNOR_REVIEWER_TOKEN"}

# Evaluation only: persists a decision but never creates an execution permit.
Invoke-RestMethod "$base/api/authorize" -Method Post -Headers $analyst -ContentType 'application/json' -Body '{"task_id":"sales-report","tool":"database.read","resource":"sales_summary","arguments":{"limit":3}}'

# Analyst read with principal-scoped idempotency.
$readHeaders = @{Authorization="Bearer $env:GOVERNOR_ANALYST_TOKEN"; 'Idempotency-Key'='read-demo-1'}
$read = Invoke-RestMethod "$base/api/actions" -Method Post -Headers $readHeaders -ContentType 'application/json' -Body '{"task_id":"sales-report","tool":"database.read","resource":"sales_summary","arguments":{"limit":3}}'
$read

# Support read; changing its resource to sales_summary is denied.
Invoke-RestMethod "$base/api/actions" -Method Post -Headers $support -ContentType 'application/json' -Body '{"task_id":"support-review","tool":"database.read","resource":"support_summary","arguments":{"limit":10}}'

# Full read -> CSV report -> pending review -> simulated send.
.\backend\scripts\demo_governor.ps1 -Decision Approve
# Separate action, rejected without sending:
.\backend\scripts\demo_governor.ps1 -Decision Reject
# Separate action, waits for policy expiry (900 seconds by default):
.\backend\scripts\demo_governor.ps1 -Decision Expire

# Authenticated reviewer polling and global integrity check.
Invoke-RestMethod "$base/api/reviews" -Headers $reviewer
Invoke-RestMethod "$base/api/audit/verify" -Headers $reviewer
Invoke-RestMethod "$base/api/audit" -Headers $analyst
Invoke-RestMethod "$base/api/metrics" -Headers $reviewer
```

The script displays the request ID, full review details and final status. Review endpoints are `GET /api/reviews/{id}`, `POST /api/reviews/{id}/approve` and `/reject`, with `{"comment":"..."}` and a reviewer bearer token. Approval has no action/body override. Comments are operator-entered, bounded, and retained; do not put secrets in them. `POST /api/actions/{id}/cancel` allows the owner to cancel before dispatch. `GET /api/actions/{id}` is owner-only; reviewers use the review detail endpoint. Polling also materializes expiry; no scheduler is required.

The lifecycle is `REVIEW_REQUIRED -> APPROVED -> REVALIDATING -> AUTHORIZED -> EXECUTING -> SUCCEEDED / FAILED / OUTCOME_UNKNOWN`. Rejection, expiry, cancellation and revalidation can terminate it as `REJECTED`, `EXPIRED`, `CANCELLED` or `BLOCKED`. Approval binds the canonical action, principal, role, task, resource and whole policy digest. Execution rechecks expiry, digest, assignment, artifact context and risk. Policy/context changes or increased reviewed risk block execution and require a new submission. Hard denials cannot be reviewed into permission. Concurrent approval attempts cannot dispatch twice. Reusing an idempotency key with the same payload returns the existing action; changing the payload returns 409. Evaluation-only and execution payloads do not share permits.

For a faster expiry demo, temporarily change `approval_seconds` in the policy file **before** creating the pending action; restore it afterwards. Changing policy while an approval is pending intentionally invalidates that approval.

## Risk and semantic assessment

Initial risk weights total 100: impact 20, sensitivity 20, blast radius 10, external egress 25, provenance uncertainty 15, recent denials 10. Each factor is bounded between zero and one. Recent denials are measured from the principal's last ten recorded actions; this is not a claim of a trained anomaly detector. Tracked artifacts have server provenance, so uncertainty is zero on supported successful paths. Categories are Low below 25, Medium from 25, High from 50, Critical from 80. Scores are policy choices, not probabilities. Risk factors, explanations and stage timings are included in responses/audit.

Low-risk reads bypass semantic work. Cases at `semantic_required_at` use semantic assessment only when enabled; otherwise the configured `BLOCK`/`ESCALATE` fallback applies. Default policy disables live semantics and requires human review for sends. An unavailable assessment configured to ESCALATE explicitly permits human resolution, subject to deterministic revalidation; BLOCK cannot be approved.

Semantic output is parsed from raw text through a strict schema with required `verdict` and `reason`. The legacy JSON repair utility remains for extraction compatibility but is not trusted by the governor. System instructions and untrusted input are separate, including Gemini's `system_instruction`. Two bounded workers enforce a five-second overall semantic response deadline covering retries/fallback. A timed-out provider task retains its slot until it exits; Python cannot forcibly cancel a blocked SDK call. Transport timeouts and a shared deadline constrain provider attempts. Saturation fails closed to the configured fallback; there is no unbounded work queue.

Set account-valid `GROQ_MODELS`, `GROQ_VISION_MODELS`, `GEMINI_MODELS` explicitly. Empty lists disable that provider path. No model availability is assumed. No live provider calls or live semantic latency measurements were run.

## Audit and operations

Audit is **tamper-evident**, not immutable. SHA-256 verification checks sequence, linkage, indexed request/role consistency and content hashes. A privileged complete rewrite or tail deletion can evade an unanchored chain check. Export `GET /api/audit/checkpoint` and retain its `{event_count, head_hash}` outside this server. Later submit that exact trusted object to `POST /api/audit/verify`. A missing/changed historical prefix fails, even if the remaining chain is internally consistent. A checkpoint next to the database is not an independent anchor; integrity after the last checkpoint still needs external retention.

All authenticated governor action decisions, including invalid JSON/schema and early permission denials, are persisted before dispatch. HTTP validation/permission failures and oversized authenticated requests get redacted denial events. Unauthenticated requests are not attributed to a principal. Raw denied payloads, credentials, headers and model text are not audited. If required pre-dispatch persistence fails, dispatch stops. Outcome persistence failure returns the request ID, `OUTCOME_UNKNOWN` and `executed=null`; startup recovery later records the uncertain state. During the current process, an uncommitted outcome can still appear as EXECUTING on polling. No exactly-once crash guarantee is claimed.

Bodies are limited to 16 KiB on action/evaluation endpoints and 2 MiB elsewhere, with a ten-second body deadline. Reads cap at 100 rows and 64 KiB serialized output. Reports use generated names, atomic replacement, file flushing and bounded sends. Liveness is `/health`; `/ready` checks identity, schema access and demo-file availability (not cloud or embeddings). Aggregate metrics require audit permission. CORS defaults to localhost:5173. Knowledge ingestion/stats require `knowledge_admin`. Blocking endpoint work runs in FastAPI's threadpool.

## Tests and benchmark

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe backend/scripts/benchmark_governor.py --samples 100 --concurrency 4
```

Actual verification: syntax compilation passed; **60 tests passed** at the final full-suite checkpoint, with dependency deprecation warnings from Chroma, Google GenAI and Starlette TestClient. Tests use temporary databases and mocked providers, including executor spies, ownership isolation, schema attacks, role/task checks, export restrictions, approval races, policy changes, restart, idempotency, audit failures/tampering, trusted-checkpoint tail deletion and HTTP authentication/limits. No real-provider integration was tested.

The corrected offline benchmark completed successfully on Windows 11, Python 3.14.4, Intel Family 6 Model 186, 16 logical CPUs. It used fresh temporary WAL/FULL databases, 3 synthetic rows, 100 samples, concurrency 4 and 10 warmups; OS caches were uncontrolled. Each sample performs one deterministic evaluation, one durable evaluation-only request and one durable execution. First execution: 35.610 ms. Throughput: 90.49 complete workload samples/s. Observed p50/p95/p99 in milliseconds:

- Deterministic: 0.341 / 0.621 / 0.856.
- Durable evaluation: 2.746 / 69.374 / 207.216.
- Adapter execution (including artifact persistence): 1.705 / 2.946 / 49.233.
- End-to-end execution: 7.336 / 71.648 / 445.381.
- Mock semantic plumbing only: 0.037 / 0.085 / 0.103. This is **not cloud inference latency**.

The <5 ms deterministic and <10 ms fast-path targets are not production guarantees; durable tail latency exceeded 10 ms under this concurrent workload. Never weaken durability to improve reported figures. Response stage timings are diagnostic snapshots; the benchmark measures wall-clock durable completion independently, including commits.

## Exact files

New modules: `api/governor.py`, `api/limits.py`, `core/governor_identity.py`, `core/governor_store.py`, `core/governor_policy.py`, `core/governor_adapters.py`, `core/governor_service.py`, `core/governor_semantic.py`, `core/governor_runtime.py`.

New supporting files: `governor_policy.json`, `tests/test_governor.py`, `scripts/benchmark_governor.py`, `scripts/demo_governor.ps1`, `GOVERNOR.md`.

Updated files: `api/main.py`, `config.py`, `core/llm_client.py`, `core/tool_executor.py`, `core/demo_data.py`, `tests/test_llm_client.py`, `requirements.txt`, `.env.example`, repository `.gitignore`.

Existing uncommitted `core/audit_store.py` and `core/permission_governor.py` are preserved. Legacy role-only helper functions are not used by the new API. Frontend files and the actual `.env` are unchanged.

## Limits and production upgrades

This is a single-host demo with static server identities and synthetic data, not a production security certification. It does not implement real delivery, distributed dispatch or general-purpose tools. Operator-controlled files/database and trusted server code are part of the trust boundary. File creation and SQLite cannot commit atomically: a crash can leave an orphan report, and ambiguous attempts require reconciliation. Filesystem durability beyond file fsync/atomic replacement depends on the OS. Activity counters and approvals are intentionally conservative; thresholds need real workload calibration. There is no automated retention/archival policy.

For production, replace demo tokens with OIDC issuer/audience/signature validation and map stable subject IDs to server-side roles/assignments. Add tenant boundaries, credential rotation, ingress rate limits, TLS, external audit checkpoints/retention, backups, structured operational telemetry, dependency pinning and workload-specific redaction. Benchmark deployment hardware and real provider latency separately. Gate future delivery adapters behind explicit destination policy and provider idempotency/reconciliation.

The PostgreSQL boundary is `Store` transactions, migrations, atomic state claims, unique idempotency/outbox keys and artifact metadata. Move these to a repository implementation with row-level locking and equivalent transaction semantics; do not replace transactional decisions with a cache. Distributed recovery would need leases/heartbeats and a reconciler rather than the current exclusive-process startup recovery. No second database backend is included.
