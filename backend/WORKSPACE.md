# Company-configurable PNG5 workspace

The company workspace is implemented in `workspace.api:app`. The existing SQLite governor and platform endpoints remain in `api.main:app`, unchanged by this extension. Use one entry point on a given port. The frontend now opens the company dashboard; `/?legacy=1` preserves the previous React screens.

**Verification boundary:** the existing regression tests and dependency-free new tests ran. PostgreSQL/SQLAlchemy integration, PDF extraction, a Vite build and browser journeys did **not** run because the required packages and frontend dependencies are not installed. No dependencies were installed, live providers called, real messages sent, or real databases migrated. The implementation needs the local setup and integration checks below before relying on the new workspace path.

## Architecture and authority

The workspace API resolves a human membership or hashed agent credential into a server-side organization/principal. Request bodies cannot choose authoritative roles or organization IDs. Humans have workspace permissions; agents have separate business roles and task assignments. Switching workspaces requires a current membership and issues a new signed token.

SQLAlchemy 2 models persist organizations, users, memberships, reviewer groups, agents, credentials, tasks, connectors, sources, policy versions, jobs, actions, artifacts, approvals, idempotency records, outbox records, audit events and legacy streams. Deployment requires PostgreSQL. SQLite is permitted only when an isolated test explicitly constructs `Database(..., testing=True)`; it is not a production fallback.

A source is untrusted evidence. PDF/text extraction creates a source revision and a DRAFT. Compilation, whether manual or optional LLM-based, writes suggestions to a draft only. Published structured rules are the authority. Draft edits invalidate validation. Publishing revalidates every reference and atomically replaces the active policy using an expected-active-version check. Published rule content is immutable through the API; clone it into a draft to change or roll it back. Archiving the active policy is prohibited.

The bounded rule language supports exact role/tool/resource/task matching, a maximum read row count, permitted formats and explicit destinations. It has no code, expressions, SQL or wildcard capabilities. Rule resolution is BLOCK before ESCALATE before ALLOW; no granting match means BLOCK. Conflicting escalation groups, unsupported capabilities, unbound citations and unresolved assumptions/ambiguities prevent publication. An explicit BLOCK overlapping an ALLOW is a valid deny override, not an ambiguous conflict.

The existing strict tool argument schemas, fixed read SQL, CSV formula escaping, risk policy and strict semantic assessor are reused. Workspace orchestration replaces the legacy fixed role matrix with published organization rules and checks organization-owned task/resource/artifact bindings. Adapter code still controls capabilities. An uploaded policy cannot create a shell, arbitrary SQL, filesystem or HTTP adapter.

Actions bind canonical input, organization, principal, policy ID/digest and context. Approvals recheck the current agent, credential, task, connector, artifact, policy and risk. Policy/context changes invalidate pending approval. All matching escalation groups must be held by the reviewer. The playground records its human initiator, who cannot approve their own request. A normal agent submission needs an agent key; a human bearer token cannot simply impersonate it through `/api/actions`.

Per-organization row locks serialize policy publication, execution claims, idempotency and audit head updates. Provider and adapter work stays outside the transaction. State/audit writes commit together. Outbox entries use the action ID as a primary key. Post-execution persistence failure returns the request ID and OUTCOME_UNKNOWN. Startup marks interrupted attempts uncertain rather than replaying them. This is not an exactly-once guarantee across crashes.

## Install and run locally

Commands below are for you to run; installation and database setup were not performed by the implementation agent.

1. Install PostgreSQL locally. Using an operator `psql` session, create a dedicated account/database:

```sql
CREATE ROLE png5 LOGIN;
\password png5
CREATE DATABASE png5 OWNER png5;
-- Separate database for optional integration/concurrency tests:
CREATE DATABASE png5_test OWNER png5;
```

2. From the repository root, install the declared packages into your environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Push-Location frontend
npm install
Pop-Location
```

Added Python packages: SQLAlchemy 2, Alembic, psycopg 3, argon2-cffi, PyJWT and pypdf. Added frontend development package: `@playwright/test`. Existing React/Vite/Vanilla CSS dependencies are retained. No Redis, Celery or Kubernetes is introduced.

3. Configure `backend/.env` or your shell. The actual `.env` was not edited.

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://png5:<URL-encoded-password>@localhost:5432/png5'
# Generate a fresh signing secret; paste its output into WORKSPACE_SIGNING_SECRET.
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
$env:WORKSPACE_SIGNING_SECRET = '<generated signing secret>'
$env:CORS_ORIGINS = 'http://localhost:5173'
$env:WORKSPACE_DEMO_MODE = 'false'
$env:POLICY_COMPILATION_LLM = 'false'
$env:WORKSPACE_POLICY_EMBEDDINGS = 'false'
$env:POLICY_URL_HOSTS = ''

.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
Push-Location backend
..\.venv\Scripts\python.exe -m workspace.cli bootstrap --email admin@example.test --workspace 'Initial workspace'
..\.venv\Scripts\python.exe -m core.demo_data
..\.venv\Scripts\python.exe -m uvicorn workspace.api:app --host 127.0.0.1 --port 8000 --workers 1 --limit-concurrency 64
Pop-Location
```

Bootstrap prompts for a 12+ character password, creates the initial administrator and grants operator-authorized workspace creation. There is no public privileged signup. Use one worker: a PostgreSQL advisory lease prevents startup recovery from racing another live workspace server. PostgreSQL lock waits are bounded to three seconds and statements to ten seconds. Apply Alembic explicitly; startup never creates tables or rewrites history.

4. In another terminal:

```powershell
Push-Location frontend
npm run dev -- --host 127.0.0.1
Pop-Location
```

Open the displayed Vite address. Its `/api` proxy targets `127.0.0.1:8000`. Production hosting needs an equivalent same-origin reverse proxy and TLS. Tokens remain in React memory and expire after 15 minutes; refresh/reopening requires sign-in. No privileged tokens are embedded in source or Vite variables. Login uses Argon2id password hashing, signed HS256 tokens, explicit issuer/audience, live membership checks and a bounded local login rate limit. This is a local account system, not enterprise SSO. OIDC with issuer/audience validation and stable subject mapping is the enterprise upgrade.

## Complete deterministic demo

The automated journey creates a fresh organization and a separate reviewer, publishes cited rules, registers and assigns an agent, reads synthetic sales, creates a real report, escalates a simulated send, approves it, then publishes a new version blocking the same destination. The changed decision comes from the new published rule, not a hardcoded demo branch.

```powershell
$env:WORKSPACE_ADMIN_EMAIL = 'admin@example.test'
$env:WORKSPACE_ADMIN_PASSWORD = '<bootstrap password>'
.\.venv\Scripts\python.exe backend/scripts/demo_workspace.py
```

The script prints organization/action IDs, not passwords or agent keys. It creates demo resource declarations and a task before validation because rules must bind real resource/task IDs. It registers the agent, assigns the task and tests connections after publication. Credentials for its separate synthetic reviewer are generated at runtime and are not printed. No external delivery or LLM call is involved. This HTTP demo has been implemented but **not run** here.

Manual dashboard journey:

1. Sign in, create a company workspace in Overview, and switch to it.
2. In Agents & Tools create a demo sales connector, report storage and simulated delivery. Create a Managers reviewer group.
3. Create a `sales-report` task with business role `data_analyst` and all three resources. It may initially have no agent assignment.
4. Upload `backend/data/sample_policies/company_policy.md` in Policies. It creates a draft without activating permission.
5. Select that draft, choose the source/task/Managers group, and generate manual suggestions. Wait for SUCCEEDED and reload the selected draft.
6. Compare every rule against its passage in the split view. Resolve assumptions by editing the rules; `assumptions` and `ambiguity` must be empty only after human review. Save, validate, inspect the diff, then publish.
7. Register an analyst agent and update the task assignment. Generate its key only if you need direct agent API access; it is displayed once. Revoking the agent revokes its credentials.
8. Provision a different human account with `review,activity,audit` and Managers membership. Existing accounts must leave the initial-password field empty. An administrator cannot reset another account's password through membership management.
9. In Demo Playground choose the agent and task, then read the sales connector with `{"limit":3}`. Use the returned artifact ID for `report.create` against report storage, then its report artifact ID for `report.send` against simulated delivery with recipient `review@example.test`.
10. Sign in as the separate reviewer in a different browser session. Inspect exact input, destination, sensitivity, source references, risk, digest and expiry. Approve. Delivery returns `delivery_mode="simulated"`; the outbox is persistent.
11. Inspect Live Activity and Audit. Clone the policy, change the send rule to BLOCK (remove its reviewer group), save, validate and publish against the active version. Repeat the same proposed send: it is now blocked.

The Policies page also supports source revisions, URL import, validation errors, job statuses, source/rule comparison and version diff. Rollback means cloning a prior version and explicitly publishing a new version, not mutating history. The Audit search accepts agent, action, decision, policy ID or timestamp text. Overview counts explicitly cover the most recent 200 actions; they are not invented lifetime metrics. List views are bounded to 200 records in this initial slice.

## Useful API calls

All routes below are on the workspace entry point. Humans authenticate with a session token; agents authenticate with their generated key. An organization ID in a body is never authority.

```powershell
$base = 'http://127.0.0.1:8000'
$login = Invoke-RestMethod "$base/api/session/login" -Method Post -ContentType 'application/json' -Body (@{email=$env:WORKSPACE_ADMIN_EMAIL;password=$env:WORKSPACE_ADMIN_PASSWORD}|ConvertTo-Json)
$human = @{Authorization="Bearer $($login.access_token)"}
Invoke-RestMethod "$base/api/session" -Headers $human
Invoke-RestMethod "$base/api/registry" -Headers $human
Invoke-RestMethod "$base/api/policies" -Headers $human
Invoke-RestMethod "$base/api/reviews" -Headers $human
Invoke-RestMethod "$base/api/audit/verify" -Headers $human
Invoke-RestMethod "$base/api/outbox" -Headers $human

# Use actual IDs returned by your organization registry.
$agent = @{Authorization='Bearer <one-time agent key>'; 'Idempotency-Key'='read-001'}
$action = @{task_id='<task ID>';tool='database.read';resource='<sales connector ID>';arguments=@{limit=3}} | ConvertTo-Json -Depth 6
Invoke-RestMethod "$base/api/authorize" -Method Post -Headers $agent -ContentType 'application/json' -Body $action
Invoke-RestMethod "$base/api/actions" -Method Post -Headers $agent -ContentType 'application/json' -Body $action
```

`/api/authorize` persists evaluation but never executes or grants a reusable permit. `/api/actions` is the agent execution boundary. `/api/playground/{agent_id}` is a separately authorized human initiation path, with initiator attribution and self-approval protection. Same principal + key + payload returns the existing action; changed payload conflicts. Action status is `/api/actions/{id}`; cancellation is `POST /api/actions/{id}/cancel`. Reviewer decisions are `POST /api/reviews/{id}/approve` or `/reject`, with `{"comment":"checked"}`. Expiry is enforced on execution and polling.

Administrative endpoints include `/api/workspaces`, `/api/members`, `/api/groups`, `/api/agents`, `/api/tasks`, `/api/connectors`, `/api/sources/upload`, `/api/sources/url`, `/api/policies`, and `/api/compilations`. Editing draft/registry records sends the record's `id`; draft saves also require `expected_revision`. Publish requires `expected_active_policy_id`, including explicit null for the first policy. Membership and individual-key revocation have explicit POST endpoints ending in `/revoke`.

Source downloads use authenticated `/api/sources/{id}/download`, never a public static folder. Artifact metadata is scoped at `/api/artifacts/{id}`. Supported connectors contain only a code-controlled kind and, for simulation, explicit `example.test` destinations: there are no user-supplied local paths, SQL, HTTP endpoints or secrets. No genuine external resource connection is claimed.

## Source ingestion, compilation and retrieval

Local storage uses generated organization/file identifiers, content hashes and a storage protocol suitable for a later object-store implementation. Protect `backend/data/private_documents` and `backend/data/workspace_reports` with OS permissions; neither is publicly served. Files are capped at 2 MiB, extracted text at 200,000 characters and PDFs at 100 pages. Image-only PDFs return an OCR-unavailable error. UTF-8 text rejects binary null bytes; PDFs require a valid signature and parser validation.

Extraction/fetching runs in a short-lived child process, limited to 12 seconds and 384 MiB. Unix also applies a CPU limit; Windows uses a Job Object memory limit. Two parser slots bound concurrent processes. Failure to establish resource limits fails extraction. Plain-text isolated extraction was verified on this Windows machine. PDF parsing still requires the uninstalled pypdf package and has not been tested here.

URL fetching is disabled until an operator configures exact `POLICY_URL_HOSTS`. It permits only HTTPS/443 with no embedded credentials. All resolved addresses must be globally routable; the connection is pinned to a validated IP while TLS verifies the original hostname. Every redirect is re-resolved/revalidated, with at most three redirects, bounded bytes and deadlines. Cookies, proxies and company credentials are not used. Compressed responses and unsupported content types are rejected. This is not merely a URL regex; there is no recursive crawler. Network fetching was not exercised live; SSRF checks and redirects were tested with mocks.

Manual compilation produces suggestions with explicit unresolved assumptions. Optional model compilation uses the existing client, separates system instructions from untrusted source content and validates raw JSON through RuleSet. Enable only with `POLICY_COMPILATION_LLM=true` and configured model IDs. It never publishes. Jobs use two bounded local workers, persist statuses, and become INTERRUPTED after restart. This is not a durable distributed queue. A provider SDK that ignores its timeout can occupy a worker until it returns; it cannot grant permission or create an unbounded queue.

`GET /api/policy-passages?q=...` returns supporting passages. Lexical matching works without embeddings. Optional Chroma indexing uses an organization-specific collection, organization metadata filtering and exact source/revision/text reconciliation. Enable `WORKSPACE_POLICY_EMBEDDINGS=true` only after locally provisioning the existing sentence-transformer model cache; `local_files_only=True` prevents implicit model downloads. `POST /api/policy-passages/index` builds the supporting index. Neither retrieval mode is consulted as execution authority. Embedding/Chroma workspace paths were not exercised in this session.

## SQLite backup and explicit legacy import

The original SQLite engine remains operational on `api.main:app`; starting the workspace engine does not touch it. Stop the legacy process before import. Its process lease prevents importing during a live legacy dispatch.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m workspace.cli import-legacy --sqlite data/governor.db --backup data/governor-pre-workspace-backup.db --owner-email admin@example.test
Pop-Location
```

The command creates a consistent SQLite backup using SQLite's backup API, verifies the historical chain, and creates a dedicated imported-demo organization. It maps only known trusted `analyst-1`/`support-1` records with matching roles and known tasks. Unknown ownership does not become ordinary action visibility. It imports trustworthy action/assignment/artifact/approval/outbox/idempotency records and emits an ownership manifest. It never changes the original database. Source content is not inferred from legacy knowledge files and no organization policy is silently published.

Original historical `event_json` strings, sequences, previous hashes and event hashes remain byte-equivalent within the labeled LegacyStream payload. They are not rehashed into the new stream. The new organization audit starts independently with an import event referencing the snapshot digest and historical head. `/api/audit/legacy` is scoped to that organization and audit permission and returns a bounded recent window. Retain the SQLite backup as the full legacy export.

Imported pending actions are cancelled, not dispatched under a different policy. Historical artifacts are marked LEGACY_READ_ONLY; their old local files are not silently relocated or exported. A new authorized read creates usable workspace artifacts. Legacy idempotency entries are retained; ID normalization can intentionally make an old key conflict. Use a deliberately new key for a new post-migration action, never blindly replay an uncertain action.

For explicit demo compatibility, set `WORKSPACE_DEMO_MODE=true` only after import. The importer hashes configured analyst/support tokens; plaintext credentials are not written to PostgreSQL. Old task/resource aliases are translated using the imported registry, while the published organization policy remains authoritative. Optional reviewer-token mapping requires explicit `DEMO_ORGANIZATION_ID` and `DEMO_REVIEWER_USER_ID`; its authority is restricted to the mapped membership's review/audit/activity permissions. New generated keys work without demo mode. The API retains `/api/authorize` and `/api/actions` meanings; action/resource IDs in the new platform are not silently interchangeable with arbitrary old IDs. Use the import manifest for historical action IDs.

The import is an operator-driven one-time transition, not continuous replication. Exact repeat snapshots are rejected. A changed snapshot with previously imported artifact IDs is not a merge workflow. Take a PostgreSQL backup before import/publish operations where rollback is needed. Alembic's destructive downgrade is disabled. Rolling back to the old process leaves post-cutover PostgreSQL actions/audits in PostgreSQL; it does not replay or merge them into SQLite.

## Tests and actual results

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend/workspace backend/migrations
.\.venv\Scripts\python.exe -m pytest backend/tests -q
node --test frontend/tests/workspace.test.js

# After dependency installation, functional workspace tests use temporary SQLite only:
.\.venv\Scripts\python.exe -m pytest backend/tests/test_workspace_integration.py -q

# PostgreSQL tests create/drop only a generated schema in an explicit *_test database:
$env:TEST_DATABASE_URL = 'postgresql+psycopg://png5:<password>@localhost:5432/png5_test'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_workspace_postgres.py -q

Push-Location frontend
npm run build
npm run lint
# Install the browser locally if needed; not run by the implementation agent:
npx playwright install chromium
npm run test:e2e
Pop-Location
```

Actual results in this session:

- Python regression/pure-rule/SSRF tests: **87 passed, 2 modules skipped**, with three existing dependency deprecation warnings. The original governor tests remain passing.
- Node client tests: **4 passed**.
- Python syntax compilation: passed for new workspace modules/migrations/scripts.
- Isolated Windows plain-text extraction: passed (one source segment).
- SQLAlchemy functional tests: **not run**; packages unavailable.
- PostgreSQL migrations, import and concurrent publish/approval/audit tests: **not run**.
- Full HTTP demo, frontend Vite build/lint and Playwright browser journeys: **not run**; dependencies unavailable.
- Live providers, live URL fetching, PDF parsing and workspace embedding integration: **not run**.

The PostgreSQL tests refuse a database name that does not end in `_test` and use a unique generated schema, never the production schema. The browser tests mock API responses and exercise the frontend publish/approval controls; they do not replace real backend integration. The deterministic demo script is the cross-layer HTTP acceptance path to run after setup.

## Exact changes for this extension

New backend files:

- `workspace/__init__.py`, `models.py`, `identity.py`, `audit.py`, `rules.py`, `sources.py`, `admin.py`, `runtime.py`, `compiler.py`, `retrieval.py`, `api.py`, `cli.py`.
- `alembic.ini`, `migrations/__init__.py`, `migrations/env.py`, `migrations/schema_0001.py`, `migrations/versions/0001_workspace.py`.
- `scripts/demo_workspace.py`, `data/sample_policies/company_policy.md`.
- `tests/test_workspace_rules.py`, `tests/test_workspace_integration.py`, `tests/test_workspace_postgres.py`.
- `WORKSPACE.md` (this guide).

New frontend files:

- `src/LegacyApp.jsx`, `src/workspaceClient.js`, `src/workspace.css`.
- `src/workspace/shared.jsx`, `Policies.jsx`, `Registry.jsx`, `Activity.jsx`.
- `playwright.config.js`, `tests/workspace.test.js`, `tests/e2e/workspace.spec.js`.

Updated: repository `.gitignore`; backend `requirements.txt` and `.env.example`; frontend `package.json`, `src/App.jsx`, `vite.config.js`. The previous turn's uncommitted governor/backend files were preserved. No real `.env`, existing SQLite database, frontend assets or existing tests were overwritten by this extension.

## Remaining limits

This code is not a multi-tenant security certification or production-readiness claim. Most new persistence paths could not be executed in the provided environment. Complete the skipped checks before deployment. There are no new performance claims.

One workspace API process per PostgreSQL database is supported initially; request threads handle concurrency, with per-organization serialization. Local storage needs filesystem backups/ACLs and a future object-store adapter for distributed deployment. File writes and PostgreSQL cannot commit atomically, so orphan reports and uncertain crash outcomes need reconciliation. Audit chains are tamper-evident, not immutable: external retained checkpoints are essential against complete rewrites and tail deletion. Imported historical events are a separate stream, not a new immutable guarantee.

Published policies are immutable through application APIs, not against a privileged database administrator. Cross-organization access is enforced in repository/API/service lookups rather than PostgreSQL row-level security. Add database roles/RLS, external identity, hardened ingress/TLS, external audit anchoring, dependency pinning, password recovery and operational retention policies before production. Membership changes are checked on each request; an already durably claimed action may finish after revocation. Only synthetic databases, protected local report artifacts and simulated delivery are implemented; no genuine external connectors or connector secrets are needed yet. When adding one, use server-side environment/secret-store references rather than accepting secrets in browser configuration.
