# PNG5 / CODE_STORM live QA report

Testing only. Generated 2026-10-01T01:15:02.019Z. Target: http://localhost:5173/ and http://127.0.0.1:8000.

**74 passed, 6 failed, 3 blocked (83 recorded checks).** These are observed check counts, not a coverage percentage or a claim that all defects are known.

## Outcome

The complete navigation did not work correctly: Live Activity could not load existing actions, and session renewal failed. The core action-execution journey did complete through real UI controls: setup → manual policy compilation → reviewed publication → sales read → CSV creation → pending review → separate-reviewer approval and simulated delivery. A separate request was rejected. A later published rule changed delivery to BLOCK without editing Python permission mappings. The complete product experience is not clean: 6 reproduced defects/gaps remain, and retained Copilot provider/retrieval execution is unavailable in this running workspace API.

The final active policy is `3719724d25ce46aeb3d02a061567e744`, which blocks delivery to review@example.test. Exactly 1 simulated outbox entry remains. No external recipient was contacted. The extra publication used to reproduce unsaved-edit loss retained the blocking rule. All synthetic records are left for inspection.

Application files were unchanged: 116 start-of-run hashes compared, 0 differences. Existing working-tree modifications predated this QA run. No services were restarted, no application fixes applied, no business fixture reseeded, and no database records or audit history deleted/reset.

## Method and boundaries

Real installed Chrome was driven with the already installed Playwright package. The in-app Browser skill was inspected but its browser list was empty; this is a documented fallback, not an API-only UI claim. No response mocks, injected provider responses or unit-test substitutes were used. Human UI logins used the user-confirmed administrator credentials and a separate synthetic reviewer in an isolated browser context. API-only security checks are labelled as such. SQL queries used a read-only PostgreSQL connection; the sales fixture was opened read-only.

Credentials were kept in private process memory, response evidence was redacted, and screenshots masked password inputs and generated-key code elements before capture. Keys and passwords are not included here. No provider/server console trace was available; current source and runtime differ, so cloud-call absence is **not independently proven**.

## Starting state

Read-only SQL confirmed one administrator account with a nonempty password hash, one CODE_STORM workspace and one active administrator membership. All business/action/artifact/policy/approval/outbox/audit counts were zero; no active policy existed. Existing demo_sales.db contained January 120000, February 135000 and March 142000. Login and overview agreed. Exact equality to a pre-reset password hash cannot be proven without a pre-reset snapshot.

## Policy review and reviewer eligibility

Source: samples/sales_policy.md; extracted revision 1. Upload alone did not activate permissions. Manual compilation job completed without requesting semantic compilation. Assumptions were reviewed before being cleared:

- Read: Source explicitly permits analyst sales reads. data_analyst is selected business role, sales-report is assigned to this agent and Sales DB. Limit 100 is a stricter implementation cap; actual request is 3.
- Create: Source explicitly permits CSV or JSON reports from authorized sales reads. Report Storage and source artifact ownership enforce the selected task.
- Delivery: Source requires human manager approval and permits only synthetic simulated delivery to review@example.test. For this authorized walkthrough, Security Reviewers is the administrator-selected approval group; separate provisioned reviewer has review permission and group membership. This tests designated reviewer authorization, not real-world managerial identity.

The UI models reviewer authorization as membership permissions plus group membership, not a standalone group role named reviewer. The test reviewer had review, activity and audit, the required group, and a different principal ID. The administrator had no reviewer-group membership, so their Approvals page correctly omitted this pending request. Its details were observed in Playground/API, and the explicit self-approval API attempt returned 403. No membership checks were weakened.

The later blocking rule follows the user's explicit instruction to impose a stricter restriction. It is not represented as a claim that the sample document itself mandates a delivery ban.

## Actual tier and latency evidence

- Read: risk 5.3 / Low; Tier 0 PASS, Tier 1 Low, Tier 2 SKIPPED, Tier 3 SUCCEEDED. Actual three rows and source artifact were verified.
- CSV creation: risk 10.3 / Low; Tier 2 SKIPPED; successful protected artifact with verified SHA-256 and matching CSV bytes.
- Delivery proposal: risk 45.3 / Medium; matched report-send, ESCALATE, Tier 2 SKIPPED, REVIEW_REQUIRED. No delivery until separate approval.
- Blocking policy: matched deny-demo-destination; Tier 0 BLOCK; subsequent risk/semantic stages SKIPPED; no new outbox entry.

The recorded risk threshold and inspected branch support deterministic skipping, but lack of independent live provider logs remains a blocked verification. stage_timings comes from backend responses and audit records; it is not a measured cloud trace. Submit-to-refreshed-UI durations include the follow-up workspace refresh and must not be interpreted as adapter execution time. Observed action submissions displayed progress and disabled duplicate submissions while in flight.

## Test matrix

Full actual payloads are in [results.json](results.json); per-request method/path/status and redacted bodies are in [network.json](network.json). Large values below are abbreviated only for readability.

| Test ID | Page/action | Expected | Actual | PASS/FAIL/BLOCKED | Evidence |
|---|---|---|---|---|---|
| ENV-01 | Running services | Frontend reachable; backend ready in workspace mode | Frontend HTTP 200; health workspace/simulated; readiness HTTP 200 | PASS | [results.json](results.json) / [network.json](network.json) |
| UI-01 | Initial sign-in screen | Login page renders | PNG5 GOVERNANCE Permission before execution.  Sign in to your company workspace. Accounts are provisioned by an administrator.  Workspace sign in Email Password Sign in  Start the workspace backend and provision an account with the bootstrap command. No public signup. | PASS | [01-sign-in.png](01-sign-in.png) |
| DB-01 | Preserved reset baseline | Only preserved administrator, workspace and membership; no active policy or test records | SELECT-only queries found one active administrator with password hash, one CODE_STORM Workspace, one administrator membership; all business/audit counts zero | PASS | [baseline-db.json](baseline-db.json) |
| FIX-01 | Synthetic sales fixture | Existing usable demo sales data | Read-only SQLite query found three sales rows; no seeding performed | PASS | [baseline-db.json](baseline-db.json) |
| UI-02 | Administrator sign-in and Overview | Successful sign-in and empty reset metrics | {"status":200,"overview":{"active_policy_id":null,"agents":0,"connectors":0,"counts":{"ALLOW":0,"BLOCK":0,"ESCALATE":0},"pending":0,"window":"latest 200 actions","capabilities":{"demo_sales":["database.read"],"demo_support":["database.read"],"report_storage":["report.create"],"simulated_delivery":["report.send"]}},"screen":true} | PASS | [02-overview.png](02-overview.png), [network.json](network.json) |
| NAV-Agents_&_Tools | Sidebar: Agents & Tools | Correct page heading; no render failure | {"heading":true,"renderError":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| NAV-Policies | Sidebar: Policies | Correct page heading; no render failure | {"heading":true,"renderError":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| NAV-Demo_Playground | Sidebar: Demo Playground | Correct page heading; no render failure | {"heading":true,"renderError":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| NAV-Approvals | Sidebar: Approvals | Correct page heading; no render failure | {"heading":true,"renderError":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| NAV-Audit | Sidebar: Audit | Correct page heading; no render failure | {"heading":true,"renderError":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| NAV-Overview | Sidebar: Overview | Correct page heading; no render failure | {"heading":true,"renderError":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| CON-demo_sales | Create Sales DB through UI | Created connector appears in its card | {"status":200,"id":"79fbda96ee25410181bdea4878fdad49","visible":true} | PASS | [network.json](network.json) |
| TEST-demo_sales | Test Sales DB through UI | Actual available result displayed inline in matching card | {"status":200,"response":{"status":"available","mode":"demo connector"},"inline":"{\n  \"status\": \"available\",\n  \"mode\": \"demo connector\"\n}","inViewport":true} | PASS | [connector-demo_sales.png](connector-demo_sales.png), [network.json](network.json) |
| CON-report_storage | Create Report Storage through UI | Created connector appears in its card | {"status":200,"id":"c41e68aad1ed4f77a2b4102df16c93fc","visible":true} | PASS | [network.json](network.json) |
| TEST-report_storage | Test Report Storage through UI | Actual available result displayed inline in matching card | {"status":200,"response":{"status":"available","mode":"local protected report storage"},"inline":"{\n  \"status\": \"available\",\n  \"mode\": \"local protected report storage\"\n}","inViewport":true} | PASS | [connector-report_storage.png](connector-report_storage.png), [network.json](network.json) |
| CON-simulated_delivery | Create Outbox through UI | Created connector appears in its card | {"status":200,"id":"40eab3cb12fb4d839dbe548cfcf9c046","visible":true} | PASS | [network.json](network.json) |
| TEST-simulated_delivery | Test Outbox through UI | Actual available result displayed inline in matching card | {"status":200,"response":{"status":"available","mode":"simulated delivery"},"inline":"{\n  \"status\": \"available\",\n  \"mode\": \"simulated delivery\"\n}","inViewport":true} | PASS | [connector-simulated_delivery.png](connector-simulated_delivery.png), [network.json](network.json) |
| CON-PERSIST | Connector refresh persistence | All three resources persist | {"names":["Outbox","Report Storage","Sales DB"],"registry":[{"id":"40eab3cb12fb4d839dbe548cfcf9c046","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Outbox","state":"ACTIVE","data":{"kind":"simulated_delivery","destinations":["review@example.test"]},"created_at":"2026-10-01T00:40:20.976501+00:00"},{"id":"c41e68aad1ed4f77a2b41… | PASS | [results.json](results.json) / [network.json](network.json) |
| AGENT-01 | Register agent in UI | Active data_analyst agent | {"id":"3bffb01cff51403a97ba006d2558b7a6","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Financial Analyst Agent","state":"ACTIVE","data":{"role":"data_analyst"},"created_at":"2026-10-01T00:43:41.896225+00:00"} | PASS | [results.json](results.json) / [network.json](network.json) |
| KEY-01 | Generate and copy key in correct agent card | Inline key, clipboard matches, feedback visible | {"status":200,"inline":true,"clipboardMatches":true,"copiedFeedback":true} | PASS | [03-agent-key-masked.png](03-agent-key-masked.png) |
| KEY-02 | Dismiss key and refresh | Key no longer rendered | {"secretCount":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| GROUP-01 | Create Security Reviewers group | Group exists | {"id":"f97e0890204242d692001394d8dd414c","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Security Reviewers","state":"ACTIVE","data":{},"created_at":"2026-10-01T00:44:57.154445+00:00"} | PASS | [results.json](results.json) / [network.json](network.json) |
| TASK-01 | Create sales-report with scope | One agent, data_analyst, three resources | {"id":"61468ae478054093b35b466d757b932a","organization_id":"430f2096245945f19785b4c1392f0d65","name":"sales-report","state":"ACTIVE","data":{"roles":["data_analyst"],"resources":["40eab3cb12fb4d839dbe548cfcf9c046","c41e68aad1ed4f77a2b4102df16c93fc","79fbda96ee25410181bdea4878fdad49"],"agents":["3bffb01cff51403a97ba006d2558b7a6"]},"created… | PASS | [results.json](results.json) / [network.json](network.json) |
| TASK-02 | Set requested task description | Description field supports Sales Report Generator | {"descriptionFieldCount":0,"stored":{"roles":["data_analyst"],"resources":["40eab3cb12fb4d839dbe548cfcf9c046","c41e68aad1ed4f77a2b4102df16c93fc","79fbda96ee25410181bdea4878fdad49"],"agents":["3bffb01cff51403a97ba006d2558b7a6"]}} | FAIL | [results.json](results.json) / [network.json](network.json) |
| REVIEWER-01 | Provision separate reviewer through UI | Active membership with review activity audit and required group | {"user_id":"aa0295460f674bf0b52a8bbe13e3f6bc"} | PASS | [results.json](results.json) / [network.json](network.json) |
| TASK-03 | Refresh assignments and verify persisted registry | Exact scope persists | {"id":"61468ae478054093b35b466d757b932a","organization_id":"430f2096245945f19785b4c1392f0d65","name":"sales-report","state":"ACTIVE","data":{"roles":["data_analyst"],"resources":["40eab3cb12fb4d839dbe548cfcf9c046","c41e68aad1ed4f77a2b4102df16c93fc","79fbda96ee25410181bdea4878fdad49"],"agents":["3bffb01cff51403a97ba006d2558b7a6"]},"created… | PASS | [04-registry.png](04-registry.png) |
| POL-01 | Upload sample policy in UI | Extracted source revision and draft, no active policy | {"upload":{"status":200,"data":{"id":"0c31f2e70b7b49639bba5485a5350639","organization_id":"430f2096245945f19785b4c1392f0d65","name":"sales_policy.md","state":"EXTRACTED","data":{"content_hash":"c36a26b7d008efc718cdfadf0676d4ac90409206f2746ef1e47d56e5d950ec9e","revision":1,"lineage":"7b41d61a82b54ccfa03535a7027981d2","uploader":"6bc1ecc0b1… | PASS | [05-policy-upload.png](05-policy-upload.png) |
| POL-02 | Generate offline draft suggestions | Completed manual compilation and three rules in editor | {"compilation":{"id":"4b786cf03c4849009b72fd35c581fc9f","state":"QUEUED"},"jobs":[{"id":"4b786cf03c4849009b72fd35c581fc9f","organization_id":"430f2096245945f19785b4c1392f0d65","name":"","state":"SUCCEEDED","data":{"source_id":"0c31f2e70b7b49639bba5485a5350639","policy_id":"edc5428aa40b4aacb3cc36057bf149f6","mode":"manual","revision":1},"c… | PASS | [06-policy-compiled.png](06-policy-compiled.png) |
| SESSION-01 | Automatic renewal during active UI work | Renew session without interruption | {"responses":[{"status":404,"response":{"detail":"Not Found"}},{"status":404,"response":{"detail":"Not Found"}},{"status":404,"response":{"detail":"Not Found"}},{"status":404,"response":{"detail":"Not Found"}},{"status":404,"response":{"detail":"Not Found"}},{"status":404,"response":{"detail":"Not Found"}},{"status":404,"response":{"detai… | FAIL | [07-session-renewal-failure.png](07-session-renewal-failure.png) |
| POL-03 | Review assumptions, save and validate | Valid references, no unresolved assumptions | {"id":"edc5428aa40b4aacb3cc36057bf149f6","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Review sales_policy.md","state":"VALIDATED","data":{"rules":[{"id":"report-send","role":"data_analyst","tool":"report.send","resource":"40eab3cb12fb4d839dbe548cfcf9c046","tasks":["61468ae478054093b35b466d757b932a"],"arguments":{"max_rows"… | PASS | [results.json](results.json) / [network.json](network.json) |
| POL-04 | Publish validated policy | Published active version | {"policy":{"id":"edc5428aa40b4aacb3cc36057bf149f6","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Review sales_policy.md","state":"PUBLISHED","data":{"rules":[{"id":"report-send","role":"data_analyst","tool":"report.send","resource":"40eab3cb12fb4d839dbe548cfcf9c046","tasks":["61468ae478054093b35b466d757b932a"],"arguments":{… | PASS | [08-policy-published.png](08-policy-published.png) |
| SESSION-02 | Sign out and sign in after publishing | Persisted setup and active policy remain | {"overview":{"active_policy_id":"edc5428aa40b4aacb3cc36057bf149f6","agents":1,"connectors":3,"counts":{"ALLOW":0,"BLOCK":0,"ESCALATE":0},"pending":0,"window":"latest 200 actions","capabilities":{"demo_sales":["database.read"],"demo_support":["database.read"],"report_storage":["report.create"],"simulated_delivery":["report.send"]}},"regist… | PASS | [08b-signin-persistence.png](08b-signin-persistence.png) |
| READ-FLIGHT | Submit action with real remote latency | Visible progress and duplicate prevention | {"submitDisabled":true,"sidebarDisabled":true,"progress":"Waiting for the server\n\nYour request is in progress. Duplicate submissions are disabled.","http":200,"elapsedMs":33153} | PASS | [results.json](results.json) / [network.json](network.json) |
| READ-01 | Read three sales rows through UI | ALLOW SUCCEEDED executed true and three rows | ALLOW; SUCCEEDED; executed=true; AUTHORIZED; request 9566cd9ec89f44fda411da190429a4a0; policy edc5428aa40b4aacb3cc36057bf149f6 | PASS | [09-read-result.png](09-read-result.png) |
| CREATE-01 | Use data-to-report shortcut | Data artifact and Report Storage preselected | {"artifact":"d593154cbb234c248f64dfc6c8d6af4e","resource":"c41e68aad1ed4f77a2b4102df16c93fc"} | PASS | [results.json](results.json) / [network.json](network.json) |
| CREATE-FLIGHT | Submit action with real remote latency | Visible progress and duplicate prevention | {"submitDisabled":true,"sidebarDisabled":true,"progress":"Waiting for the server\n\nYour request is in progress. Duplicate submissions are disabled.","http":200,"elapsedMs":38490} | PASS | [results.json](results.json) / [network.json](network.json) |
| CREATE-02 | Create CSV through UI | ALLOW SUCCEEDED report artifact | ALLOW; SUCCEEDED; executed=true; AUTHORIZED; request 712806e802df4818b03cf5e79135c65a; policy edc5428aa40b4aacb3cc36057bf149f6 | PASS | [10-report-result.png](10-report-result.png) |
| SEND-01 | Use report-to-delivery shortcut | Report artifact and Outbox preselected | {"artifact":"db82cd93e91f40ec8ce18eab2bc95513","resource":"40eab3cb12fb4d839dbe548cfcf9c046","recipient":"review@example.test"} | PASS | [results.json](results.json) / [network.json](network.json) |
| SEND-FLIGHT | Submit action with real remote latency | Visible progress and duplicate prevention | {"submitDisabled":true,"sidebarDisabled":true,"progress":"Waiting for the server\n\nYour request is in progress. Duplicate submissions are disabled.","http":200,"elapsedMs":29847} | PASS | [results.json](results.json) / [network.json](network.json) |
| SEND-02 | Propose delivery in UI | ESCALATE REVIEW_REQUIRED, executed false, empty outbox | ESCALATE; REVIEW_REQUIRED; executed=false; HUMAN_REVIEW_REQUIRED; request c1aca6ee3cef42d29c0b6b0be1578e72; policy edc5428aa40b4aacb3cc36057bf149f6 | PASS | [11-delivery-pending.png](11-delivery-pending.png) |
| REVIEW-01 | Initiator opens Approvals | Only reviews eligible for current group visible | {"snapshot":"PNG5\nGOVERNANCE\n\nCOMPANY WORKSPACE\n\nWorkspace\nCODE_STORM Workspace\nOverview\nAgents & Tools\nPolicies\nDemo Playground\nLive Activity\nApprovals\nAudit\nDEMO RESOURCES\n\nSynthetic data.\nSimulated delivery.\n\nSign out\n\nAGENT PERMISSION GOVERNOR\n\nApprovals\nRefresh\n\nRefreshing workspace...\n\nNo pending reviews\… | PASS | [12-admin-approvals.png](12-admin-approvals.png) |
| REVIEW-02 | Initiator attempts self-approval by API | 403 self-approval forbidden | {"status":403,"data":{"detail":"You cannot approve your own action"}} | PASS | [results.json](results.json) / [network.json](network.json) |
| REVIEW-03 | Separate reviewer UI login and eligibility | Different principal, required group and review permission | {"http":200,"session":{"principal_id":"aa0295460f674bf0b52a8bbe13e3f6bc","organization_id":"430f2096245945f19785b4c1392f0d65","permissions":["activity","audit","review"],"groups":["f97e0890204242d692001394d8dd414c"],"workspaces":[{"id":"430f2096245945f19785b4c1392f0d65","name":"CODE_STORM Workspace"}],"can_create_workspaces":false}} | PASS | [results.json](results.json) / [network.json](network.json) |
| REVIEW-04 | Separate reviewer approves exact action in UI | Revalidation, SUCCEEDED, simulated delivery, one outbox | ALLOW; SUCCEEDED; executed=true; REVIEW_APPROVED; request c1aca6ee3cef42d29c0b6b0be1578e72; policy edc5428aa40b4aacb3cc36057bf149f6 | PASS | [14-approved-delivery.png](14-approved-delivery.png) |
| REVIEW-05 | Retry approval API | 409 resolved; still exactly one outbox | {"retry":{"status":409,"data":{"detail":"Action is not pending review"}},"outboxCount":1} | PASS | [results.json](results.json) / [network.json](network.json) |
| CREATE-03 | Read-only DB and real CSV corroboration | Correct owner/task/source and exact three sales rows | {"metadata":{"id":"db82cd93e91f40ec8ce18eab2bc95513","organization_id":"430f2096245945f19785b4c1392f0d65","name":"","state":"ACTIVE","data":{"principal_id":"3bffb01cff51403a97ba006d2558b7a6","task_id":"61468ae478054093b35b466d757b932a","resource":"c41e68aad1ed4f77a2b4102df16c93fc","sensitivity":"internal","kind":"report","rows":[{"month":… | PASS | [pre-review-db.json](pre-review-db.json) |
| REJECT-SEND-FLIGHT | Submit action with real remote latency | Visible progress and duplicate prevention | {"submitDisabled":true,"sidebarDisabled":true,"progress":"Waiting for the server\n\nYour request is in progress. Duplicate submissions are disabled.","http":200,"elapsedMs":38737} | PASS | [results.json](results.json) / [network.json](network.json) |
| REVIEW-06 | Reviewer rejects separate action in UI | REJECTED executed false and still one outbox | BLOCK; REJECTED; executed=false; REVIEW_REJECTED; request 4b1a0e475dac4db48bc92d734026a121; policy edc5428aa40b4aacb3cc36057bf149f6 | PASS | [15-rejected-delivery.png](15-rejected-delivery.png) |
| DYNAMIC-01 | Clone, edit, save, validate and publish deny policy in UI | New PUBLISHED policy explicitly denies demo destination | {"validated":"VALIDATED","published":{"id":"82f559acd8e84c30a885a49a8d71f038","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Review sales_policy.md (new version)","state":"PUBLISHED","data":{"rules":[{"id":"deny-demo-destination","role":"data_analyst","tool":"report.send","resource":"40eab3cb12fb4d839dbe548cfcf9c046","tasks"… | PASS | [16-block-policy.png](16-block-policy.png) |
| DYNAMIC-SEND-FLIGHT | Submit action with real remote latency | Visible progress and duplicate prevention | {"submitDisabled":true,"sidebarDisabled":true,"progress":"Waiting for the server\n\nYour request is in progress. Duplicate submissions are disabled.","http":200,"elapsedMs":40093} | PASS | [results.json](results.json) / [network.json](network.json) |
| DYNAMIC-02 | Repeat same delivery under new policy in UI | BLOCK with new version and deny-demo-destination; no delivery | BLOCK; BLOCKED; executed=false; POLICY_BLOCK; request dce005bf551946f3841d285ce1354d88; policy 82f559acd8e84c30a885a49a8d71f038 | PASS | [17-policy-blocked-action.png](17-policy-blocked-action.png) |
| ERROR-JSON | Enter malformed policy JSON | Inline error and disabled save/publish | {"alerts":["Rules must be valid JSON."],"saveDisabled":true,"publishDisabled":true} | PASS | [24-invalid-policy-json.png](24-invalid-policy-json.png) |
| POL-UNSAVED | Edit VALIDATED rule then click Publish validated policy without saving | Prevent publishing stale rules, or save and validate visible edits | {"before":{"maxRows":2,"notice":true,"publishEnabled":true},"response":{"status":200,"data":{"id":"3719724d25ce46aeb3d02a061567e744","organization_id":"430f2096245945f19785b4c1392f0d65","name":"Review sales_policy.md (new version) (new version)","state":"PUBLISHED","data":{"rules":[{"id":"deny-demo-destination","role":"data_analyst","tool… | FAIL | [26-unsaved-after-publish.png](26-unsaved-after-publish.png) |
| SEC-MISSING | API action with missing credential | 401 rejection | {"status":401,"data":{"detail":"Authentication required"}} | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-INVALID | API action with invalid credential | 401 rejection | {"status":401,"data":{"detail":"Invalid or revoked credential"}} | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-TASK | Synthetic task payload | BLOCK before execution; TASK_DENIED | BLOCK; BLOCKED; executed=false; TASK_DENIED; request 1a1e5d56f48d4f26967308d6036a88f6; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-RESOURCE | Synthetic resource payload | BLOCK before execution; TASK_DENIED | BLOCK; BLOCKED; executed=false; TASK_DENIED; request 515b2840957941c09c84242dd3ec476e; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-EXTRA | Synthetic extra payload | BLOCK before execution; INVALID_ARGUMENTS | BLOCK; BLOCKED; executed=false; INVALID_ARGUMENTS; request 6825ca306afe4e71a43e83b64f402d20; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-SQL | Synthetic sql payload | BLOCK before execution; INVALID_ARGUMENTS | BLOCK; BLOCKED; executed=false; INVALID_ARGUMENTS; request dc04fa13104a411f888e53d8e131a81a; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-SHELL | Synthetic shell payload | BLOCK before execution; INVALID_ARGUMENTS | BLOCK; BLOCKED; executed=false; INVALID_ARGUMENTS; request b233588442604a809ace7b20a664ea34; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-PATH | Synthetic path payload | BLOCK before execution; INVALID_ARGUMENTS | BLOCK; BLOCKED; executed=false; INVALID_ARGUMENTS; request ea2aab0e10bc4841a79c6785c99a24cc; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-TOOL | Synthetic tool payload | BLOCK before execution; TOOL_NOT_SUPPORTED | BLOCK; BLOCKED; executed=false; TOOL_NOT_SUPPORTED; request 32c5fda61f744cf1abe15beda3c5c7c9; policy 3719724d25ce46aeb3d02a061567e744 | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-IDEMPOTENCY | Repeat same key and then change payload | Same successful request/artifact; changed payload 409 | {"one":{"status":200,"data":{"decision":"ALLOW","reason_code":"AUTHORIZED","reason":"Published rules and current context evaluated","role":"data_analyst","executed":true,"result":{"rows":[{"month":"January","total_sales":120000},{"month":"February","total_sales":135000},{"month":"March","total_sales":142000}],"row_count":3,"artifact_id":"… | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-ARTIFACT-AUTH | Read artifact metadata without authentication | 401; no anonymous artifact access | {"status":401,"data":{"detail":"Authentication required"}} | PASS | [results.json](results.json) / [network.json](network.json) |
| SEC-ISOLATION | Second workspace attempts original workspace record access | 404 original action/artifact/review and empty scoped registry | {"checks":[{"path":"/api/actions/9566cd9ec89f44fda411da190429a4a0","status":404,"data":{"detail":"Record not found"}},{"path":"/api/artifacts/db82cd93e91f40ec8ce18eab2bc95513","status":404,"data":{"detail":"Record not found"}}],"registry":{"status":200,"data":{"agents":[],"tasks":[],"connectors":[],"groups":[]}},"review":{"status":404,"da… | PASS | [18-second-workspace-created.png](18-second-workspace-created.png) |
| UI-PATTERN | Check business-role browser validation with invalid role | Browser rejects uppercase/spaces/punctuation | {"pattern":"[a-z][a-z0-9_-]{1,49}","value":"INVALID ROLE!","valid":true,"patternMismatch":false,"validationMessage":""} | FAIL | [27-invalid-role-pattern.png](27-invalid-role-pattern.png) |
| KEY-SCROLL | Generate another test key with button at viewport bottom | New banner scrolls into view before any further interaction | {"before":{"bottom":979.546875,"viewport":1000,"scrollY":139},"after":{"top":811.546875,"bottom":999.921875,"viewport":1000,"scrollY":365},"inView":true,"credentialId":"6ade157b6f0b44bb912efb4d20dfa824"} | PASS | [28-key-autoscroll-masked.png](28-key-autoscroll-masked.png) |
| LLM-INSTRUMENTATION | Independently verify no cloud calls for deterministic actions | Provider/server trace corroborates no external call | {"readTiers":{"tier0":"PASS","tier1":"Low","tier2":"SKIPPED","tier3":"SUCCEEDED"},"reportTiers":{"tier0":"PASS","tier1":"Low","tier2":"SKIPPED","tier3":"SUCCEEDED"},"readRisk":5.3,"reportRisk":10.3,"sourceBranch":"workspace/runtime.py:175 calls assess only at semantic_required_at (50); recorded scores were 5.3 and 10.3","limitation":"Exis… | BLOCKED | [results.json](results.json) / [network.json](network.json) |
| DB-HASH-HISTORY | Verify historic password-hash preservation | Compare pre-reset and current hash | Current administrator, nonempty hash, workspace and membership exist and configured credentials work. No pre-reset hash snapshot was supplied, so exact historic hash equality cannot be proven. | BLOCKED | [baseline-db.json](baseline-db.json) |
| COPILOT-01 | Inspect governor navigation for Copilot switcher | Copilot hidden per selected preference | {"switcherCount":0} | PASS | [results.json](results.json) / [network.json](network.json) |
| COPILOT-02 | Open retained legacy route directly | Render retained layout and inspect retrieval label | {"url":"http://localhost:5173/?legacy","label":"AI Copilot Mode (Pinecone RAG + Multimodal)","actualImplementation":"backend/core/rag.py Chroma PersistentClient; backend/config.py CHROMA_DIR"} | FAIL | [21-copilot-layout.png](21-copilot-layout.png) |
| COPILOT-03 | Submit benign query in retained UI | A configured backend response or explicit setup limitation | {"response":{"status":404,"data":{"detail":"Not Found"}},"inputPreserved":true,"snapshot":"AI Copilot Mode (Pinecone RAG + Multimodal)\n← Switch to PNG5 Governor Workspace\n⚡\nCODE_STORM\nPRODUCTION GENAI PLATFORM\nGroq: llama-3.3-70b\nGemini: 2.5-flash\nVector: Pinecone\nCHECKING\n💬 AI Copilot (RAG)\n📷 Multimodal Extraction\n📚 Vector … | BLOCKED | [22-copilot-query-error.png](22-copilot-query-error.png) |
| COPILOT-04 | Click switch-back from legacy UI | Original governor session and workspace retained | {"url":"http://localhost:5173/","session":{"principal_id":"6bc1ecc0b19f4dceb42aab3abd34ca72","organization_id":"430f2096245945f19785b4c1392f0d65","permissions":["activity","agents","audit","connectors","drafts","members","playground","publish","review","sources"],"groups":[],"workspaces":[{"id":"430f2096245945f19785b4c1392f0d65","name":"C… | PASS | [23-governor-return.png](23-governor-return.png) |
| NAV-Live_Activity | Open Live Activity | Recorded real actions visible | {"snapshot":"PNG5\nGOVERNANCE\n\nCOMPANY WORKSPACE\n\nWorkspace\nCODE_STORM Workspace\nQA Isolation Workspace 20261001\nOverview\nAgents & Tools\nPolicies\nDemo Playground\nLive Activity\nApprovals\nAudit\nDEMO RESOURCES\n\nSynthetic data.\nSimulated delivery.\n\nSign out\n\nAGENT PERMISSION GOVERNOR\n\nLive Activity\nRefresh\n\nSome data… | FAIL | [19-live-activity.png](19-live-activity.png) |
| AUDIT-01 | Verify chain and export checkpoint through UI | Valid stream; exported count/head match verification | {"verify":{"valid":true,"organization_id":"430f2096245945f19785b4c1392f0d65","event_count":52,"head_hash":"01ed468013d18dd3cbe125b4a5aee81ce4b4f8a77fae3495b9c1b4880c17316b","protection":"Tamper-evident; retain checkpoints independently. Complete rewrites and unanchored tail deletion are not independently detectable."},"checkpoint":{"valid… | PASS | [20-audit-checkpoint.png](20-audit-checkpoint.png) |
| AUDIT-02 | Compare retained checkpoint in UI | Valid checkpoint | {"status":200,"data":{"valid":true,"organization_id":"430f2096245945f19785b4c1392f0d65","event_count":52,"head_hash":"01ed468013d18dd3cbe125b4a5aee81ce4b4f8a77fae3495b9c1b4880c17316b","protection":"Tamper-evident; retain checkpoints independently. Complete rewrites and unanchored tail deletion are not independently detectable."}} | PASS | [results.json](results.json) / [network.json](network.json) |
| AUDIT-03 | Correlate action, reviewer and policy events | Publishing, execution, review, revalidation, rejection and block present | {"events":[{"sequence":38,"event_type":"policy.published","policy_id":"3719724d25ce46aeb3d02a061567e744"},{"sequence":35,"event_type":"action.transition","request_id":"dce005bf551946f3841d285ce1354d88","state":"BLOCKED","previous_state":null,"reviewer_id":null},{"sequence":34,"event_type":"policy.published","policy_id":"82f559acd8e84c30a8… | PASS | [results.json](results.json) / [network.json](network.json) |
| ACTIVITY-PERFORMANCE | Measure real API activity list with browser polling stopped | Existing actions available to independent 60-second diagnostic | {"http":200,"durationMs":27041,"uiTimeoutMs":30000,"count":13} | PASS | [results.json](results.json) / [network.json](network.json) |
| CODE-UNCHANGED | Compare application files to start-of-run hashes | No application source changes | {"filesCompared":116,"changed":[]} | PASS | [source-baseline.json](source-baseline.json) |
| DATA-VERIFY | Verify CSV bytes, digest, ownership and lineage against SQL records | Exact rows, digest, organization, agent, task and source | {"csvDigest":"7a33bc136e45d1b183d6d0a9b5c9368a7b37be2a72d7fbc45a4cef69ae0ee61e","digestMatches":true,"rowsMatch":true,"artifact":{"id":"db82cd93e91f40ec8ce18eab2bc95513","organization_id":"430f2096245945f19785b4c1392f0d65","name":"","state":"ACTIVE","data":{"principal_id":"3bffb01cff51403a97ba006d2558b7a6","task_id":"61468ae478054093b35b4… | PASS | [final-db.json](final-db.json) |
| AUDIT-DB | Recompute SHA-256 chain from read-only SQL snapshot | Every link, stored head and exported checkpoint agree | {"eventCount":52,"headHash":"01ed468013d18dd3cbe125b4a5aee81ce4b4f8a77fae3495b9c1b4880c17316b","organizationSequence":52,"valid":true} | PASS | [final-db.json](final-db.json) |
| SEC-DB | Corroborate denied actions and idempotency with SQL | Denied actions never execute; single idempotent artifact/action; one outbox | {"deniedStates":[{"id":"1a1e5d56f48d4f26967308d6036a88f6","state":"BLOCKED","executed":false},{"id":"515b2840957941c09c84242dd3ec476e","state":"BLOCKED","executed":false},{"id":"6825ca306afe4e71a43e83b64f402d20","state":"BLOCKED","executed":false},{"id":"dc04fa13104a411f888e53d8e131a81a","state":"BLOCKED","executed":false},{"id":"b2335884… | PASS | [final-db.json](final-db.json) |
| EVIDENCE-REDACTION | Scan textual evidence for private test credentials | No private credential values in saved artifacts | {"scannedFiles":19,"leaks":[]} | PASS | [results.json](results.json) / [network.json](network.json) |

## Reproduced defects and requirement gaps

### NAV-Live_Activity: Activity refresh times out and shows a false empty state despite persisted actions

- Severity: High.
- Reproduction: Complete the walkthrough and security checks (13 stored actions); sign in again or return from the retained Copilot page; open Live Activity and wait for refresh.
- Visible result/error: Some data could not refresh. actions: The request took too long. Beneath it: No actions yet. Publish a policy and submit an action in Demo Playground.
- Request/status: GET /api/actions → client abort at the 30-second transport deadline; no HTTP response reached the UI on those attempts..
- Redacted response: No response body for the aborted UI calls. Read-only SQL confirms persisted action rows; a separate measured API request is recorded in ACTIVITY-PERFORMANCE.
- Browser/server error: Browser requestfailed: net::ERR_ABORTED. Unlike mutation-related cancellation, these recur while the page is idle and display the explicit timeout message.
- Expected: The activity endpoint should return within the supported UI deadline; failure to load must not be presented as an empty successful result or imply that saved data disappeared.
- Cause: Inference: remote database round trips in per-action status hydration exceed the 30-second frontend deadline as history grows. The API loops through actions and looks up artifact/approval rows individually. On a new session, failed sections retain their initial empty arrays; Activity renders No actions yet without considering load failure.
- Source reference: frontend/src/workspaceClient.js:12–23; frontend/src/workspace/useWorkspace.js:48–73; frontend/src/workspace/Activity.jsx:8; backend/workspace/api.py:401–406; backend/workspace/runtime.py:346–368. These references describe the inspected source; deployment alignment is not assumed.
- Evidence: 19-live-activity.png; results.json NAV-Live_Activity and ACTIVITY-PERFORMANCE; browser-errors.json; final-db.json.

### POL-UNSAVED: Publishing a VALIDATED policy silently discards newer editor changes

- Severity: High.
- Reproduction: Clone the active policy; validate it; change database-read.arguments.max_rows from 100 to 2 in Structured rules; leave the visible Unsaved changes notice; click Publish validated policy without Save.
- Visible result/error: No error. The publish succeeds and the editor reverts to 100.
- Request/status: POST /api/policies/3719724d25ce46aeb3d02a061567e744/publish → 200.
- Redacted response: state=PUBLISHED, database-read.arguments.max_rows=100; requested editor value was 2.
- Browser/server error: No browser exception is necessary; this is a successful request for stale persisted rules.
- Expected: Block publication while dirty or save and validate the exact visible edits before publishing.
- Cause: Established control flow: publishPolicy saves dirty rules only inside selected.state === DRAFT. A VALIDATED draft bypasses saving, then edit(p) clears the newer editor contents.
- Source reference: frontend/src/workspace/Policies.jsx:78–95, 41–46. These references describe the inspected source; deployment alignment is not assumed.
- Evidence: 25-unsaved-before-publish.png, 26-unsaved-after-publish.png; results.json POL-UNSAVED.

### SESSION-01: Active-session renewal calls a route missing from the running server

- Severity: High.
- Reproduction: Sign in; keep interacting with the workspace until the token enters its renewal window. Observe repeated renewal attempts.
- Visible result/error: Could not extend your session. Save your work; you may need to sign in again.
- Request/status: POST /api/session/refresh → 404, repeatedly about every 10 seconds.
- Redacted response: {"detail":"Not Found"}
- Browser/server error: Browser console: Failed to load resource: the server responded with a status of 404 (Not Found).
- Expected: The deployed backend should support the frontend renewal contract; retries should not repeatedly create sticky error messages.
- Cause: Inference: stale process or deployment/source mismatch. Current workspace/api.py defines the route; the running OpenAPI and actual requests do not. renewSession catches non-401 failures without backoff/marking the attempt complete.
- Source reference: frontend/src/workspace/useWorkspace.js:107–138; backend/workspace/api.py:229. These references describe the inspected source; deployment alignment is not assumed.
- Evidence: 07-session-renewal-failure.png; network.json; browser-errors.json.

### UI-PATTERN: Business-role browser validation pattern is invalid in Chrome

- Severity: Medium.
- Reproduction: Open Agents & Tools; set Business role to INVALID ROLE!; inspect native validity. No invalid agent was submitted or created.
- Visible result/error: No native validation message; checkValidity returned true.
- Request/status: No HTTP request is needed; native input validation failure..
- Redacted response: pattern=[a-z][a-z0-9_-]{1,49}; valid=true; patternMismatch=false.
- Browser/server error: Console: Pattern attribute value … is not a valid regular expression … /v: Invalid character in character class.
- Expected: The browser should reject a role that violates the displayed schema before submission.
- Cause: Inference supported by the console and source: the hyphen inside the HTML pattern character class is not escaped for the browser v-flag regex grammar. Server-side validation remains a separate control.
- Source reference: frontend/src/workspace/Registry.jsx:183. These references describe the inspected source; deployment alignment is not assumed.
- Evidence: 27-invalid-role-pattern.png; results.json UI-PATTERN; browser-errors.json.

### TASK-02: Requested task description cannot be entered

- Severity: Low / requirement gap.
- Reproduction: Open Create a scoped task and inspect its fields; create sales-report and inspect its persisted data.
- Visible result/error: No Description field exists.
- Request/status: POST /api/tasks → 200 for supported task fields.
- Redacted response: Task data contains roles, resources and agents, but no description.
- Browser/server error: No browser/server exception.
- Expected: The requested Sales Report Generator description should be enterable and persisted if that workflow is supported.
- Cause: Established schema/UI gap: neither the form nor TaskInput provides a description property.
- Source reference: frontend/src/workspace/Registry.jsx (4. Create a scoped task); backend/workspace/api.py:494. These references describe the inspected source; deployment alignment is not assumed.
- Evidence: 04-registry.png; results.json TASK-02.

### COPILOT-02: Retained Copilot layout labels Chroma retrieval as Pinecone

- Severity: Low.
- Reproduction: Directly open /?legacy. The governor switcher itself is hidden, as requested. Read the Copilot banner and inspect the retrieval implementation.
- Visible result/error: AI Copilot Mode (Pinecone RAG + Multimodal)
- Request/status: Frontend route renders; no retrieval request is needed to observe the label..
- Redacted response: Repository retrieval code instantiates chromadb.PersistentClient with CHROMA_DIR.
- Browser/server error: Separate benign query fails because the running workspace API lacks /api/process; see blocked setup below.
- Expected: Label should describe the configured store or avoid naming a store until configured.
- Cause: Established static-label mismatch; this does not prove a live Chroma query ran.
- Source reference: frontend/src/LegacyApp.jsx:15; backend/core/rag.py:29; backend/config.py:67. These references describe the inspected source; deployment alignment is not assumed.
- Evidence: 21-copilot-layout.png; results.json COPILOT-02.

## Setup blockers, expected denials and remaining limits

- Copilot /api/process returned 404 with {"detail":"Not Found"}. The retained UI preserved the benign query, showed the error, and its switch-back returned to the original workspace session. The governor has no Copilot switcher, consistent with the user's preference to hide it. This diagnostic used /?legacy directly; no missing switcher click is claimed. Provider/retrieval success is BLOCKED by the absent runtime route. Pinecone is not the configured repository implementation; live Chroma availability was not verified.
- Independent provider/log confirmation of no cloud calls is BLOCKED. Reported Tier 2 SKIPPED is corroborated by persisted action/audit fields and the inspected risk branch, not external instrumentation.
- Exact historic password-hash preservation is BLOCKED without a pre-reset comparison snapshot. Current configured credentials worked.
- Expected security denials are PASS: 401 for missing/invalid credentials; 403 self-approval; 409 duplicate resolved approval and changed idempotent payload; 404 foreign-workspace records; governed BLOCK responses for malformed/unsupported/unassigned actions. A governed denial may correctly use HTTP 200 while decision=BLOCK and executed=false.
- Browser net::ERR_ABORTED events occurred around cancellation of polling when mutations/session changes began and when the reviewer context closed. These are retained in browser-errors.json and are not automatically counted as defects. The initial generic console 404 has no captured request path; it is not attributed to a guessed URL.
- A download control/route was not offered in the tested UI. The actual local CSV and authenticated artifact metadata were checked; anonymous metadata access was denied. No claim of a tested download button is made.
- No live audit tampering was performed. Chain verification is tamper-evident, not immutable storage or a complete security guarantee. No provider outage injection, browser crash, concurrent multi-user policy-edit stress test, accessibility audit, or exhaustive fuzzing was performed.

## Audit result

UI Verify chain and Export checkpoint matched; Compare checkpoint succeeded. Read-only SQL recomputation matched 52 events and head `01ed468013d18dd3cbe125b4a5aee81ce4b4f8a77fae3495b9c1b4880c17316b`. Events include policy publication, action outcomes, the approved review's reviewer identity, APPROVED → REVALIDATING → AUTHORIZED → EXECUTING → SUCCEEDED, rejection and policy block. The exported checkpoint is [checkpoint.json](checkpoint.json); retain a copy outside this server if it is to serve as an independent trust anchor.

## Prioritized fixes (not implemented)

1. Prevent publication of stale persisted rules when a VALIDATED draft has newer unsaved edits. Save and validate exactly what the user sees, or block publication clearly.
2. Reduce activity endpoint latency (including per-action database round trips) and distinguish failed loading from an empty successful result. Keep known records visible and provide a focused retry.
3. Align the running backend with session renewal and bound repeated renewal-error feedback. No server restart was performed during this test.
4. Correct the Business role HTML pattern and verify native validity in the actual browser.
5. Add task description support if this is a required product field.
6. Correct retained Copilot store labels and keep its entry point hidden until its backend routes are configured.

## Records and retained files

- Original workspace: `430f2096245945f19785b4c1392f0d65`
- Admin user: `6bc1ecc0b19f4dceb42aab3abd34ca72`
- Agent: `3bffb01cff51403a97ba006d2558b7a6`
- Reviewer group: `f97e0890204242d692001394d8dd414c`
- Reviewer user: `aa0295460f674bf0b52a8bbe13e3f6bc`
- Reviewer email: `qa-reviewer-20261001@example.test`
- Task: `61468ae478054093b35b466d757b932a`
- Uploaded source: `0c31f2e70b7b49639bba5485a5350639`
- Compilation job: `4b786cf03c4849009b72fd35c581fc9f`
- Original published policy: `edc5428aa40b4aacb3cc36057bf149f6`
- First blocking policy: `82f559acd8e84c30a885a49a8d71f038`
- Final active policy (unsaved-edit reproduction): `3719724d25ce46aeb3d02a061567e744`
- Additional unassigned task: `87e0321df1e04cc28a5c8dce00c7648a`
- Additional unassigned connector: `0522e5982b1b4e92a641d748cd499855`
- Isolation workspace: `bacb024dcfe14794973f642e8829dacf`
- Data read request: `9566cd9ec89f44fda411da190429a4a0`
- Report creation request: `712806e802df4818b03cf5e79135c65a`
- Approved send / outbox: `c1aca6ee3cef42d29c0b6b0be1578e72`
- Rejected send: `4b1a0e475dac4db48bc92d734026a121`
- Blocked send: `dce005bf551946f3841d285ce1354d88`
- Idempotent read: `69aa614ddf73467193f258fff8940c86`
- Data artifact: `d593154cbb234c248f64dfc6c8d6af4e`
- CSV report artifact: `db82cd93e91f40ec8ce18eab2bc95513`
- Idempotent data artifact: `a9fb3d8ab7614a60bca4826deaa5922d`
- Sales DB: `79fbda96ee25410181bdea4878fdad49`
- Report Storage: `c41e68aad1ed4f77a2b4102df16c93fc`
- Outbox: `40eab3cb12fb4d839dbe548cfcf9c046`
- Generated credential record (secret omitted): `adb64c93066843ae994c3d4e31bae8b2`
- Generated credential record (secret omitted): `6ade157b6f0b44bb912efb4d20dfa824`
- Security TASK request: `1a1e5d56f48d4f26967308d6036a88f6`
- Security RESOURCE request: `515b2840957941c09c84242dd3ec476e`
- Security EXTRA request: `6825ca306afe4e71a43e83b64f402d20`
- Security SQL request: `dc04fa13104a411f888e53d8e131a81a`
- Security SHELL request: `b233588442604a809ace7b20a664ea34`
- Security PATH request: `ea2aab0e10bc4841a79c6785c99a24cc`
- Security TOOL request: `32c5fda61f744cf1abe15beda3c5c7c9`

- CSV: `backend/data/workspace_reports/430f2096245945f19785b4c1392f0d65/db82cd93e91f40ec8ce18eab2bc95513.csv`
- All final row IDs, states, owners and audit events: [final-db.json](final-db.json).
- Baseline: [baseline-db.json](baseline-db.json).
- Before approval: [pre-review-db.json](pre-review-db.json), including zero approvals/outbox and the two artifacts.
- Redacted UI/API evidence: [network.json](network.json).
- Browser errors and cancellations: [browser-errors.json](browser-errors.json).
- Test harness and journey scripts: this directory's .mjs and read_db.py files. They are QA artifacts only.

## Screenshots

- [01-sign-in.png](01-sign-in.png)
- [02-overview.png](02-overview.png)
- [03-agent-key-masked.png](03-agent-key-masked.png)
- [04-registry.png](04-registry.png)
- [05-policy-upload.png](05-policy-upload.png)
- [06-policy-compiled.png](06-policy-compiled.png)
- [07-session-renewal-failure.png](07-session-renewal-failure.png)
- [08-policy-published.png](08-policy-published.png)
- [08b-signin-persistence.png](08b-signin-persistence.png)
- [09-read-result.png](09-read-result.png)
- [10-report-result.png](10-report-result.png)
- [11-delivery-pending.png](11-delivery-pending.png)
- [12-admin-approvals.png](12-admin-approvals.png)
- [13-reviewer-pending.png](13-reviewer-pending.png)
- [14-approved-delivery.png](14-approved-delivery.png)
- [15-rejected-delivery.png](15-rejected-delivery.png)
- [16-block-policy.png](16-block-policy.png)
- [17-policy-blocked-action.png](17-policy-blocked-action.png)
- [18-second-workspace-created.png](18-second-workspace-created.png)
- [19-live-activity.png](19-live-activity.png)
- [20-audit-checkpoint.png](20-audit-checkpoint.png)
- [21-copilot-layout.png](21-copilot-layout.png)
- [22-copilot-query-error.png](22-copilot-query-error.png)
- [23-governor-return.png](23-governor-return.png)
- [24-invalid-policy-json.png](24-invalid-policy-json.png)
- [25-unsaved-before-publish.png](25-unsaved-before-publish.png)
- [26-unsaved-after-publish.png](26-unsaved-after-publish.png)
- [27-invalid-role-pattern.png](27-invalid-role-pattern.png)
- [28-key-autoscroll-masked.png](28-key-autoscroll-masked.png)
- [connector-demo_sales.png](connector-demo_sales.png)
- [connector-report_storage.png](connector-report_storage.png)
- [connector-simulated_delivery.png](connector-simulated_delivery.png)

## Browser-error inventory

All raw, redacted entries are in browser-errors.json. UI runtime page exceptions: 0. Console errors include the invalid role pattern and HTTP 404s. The proven action-list timeout is distinct from expected aborts on mutation/session changes. No unobserved server exception is inferred from these client events.
