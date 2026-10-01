# CODE_STORM Enterprise Governance — Complete Navigation Flow & User Guide

This guide describes the end-to-end user navigation flow for the **PNG5 Enterprise Governor** and the **AI Copilot (Pinecone RAG)** modes in the CODE_STORM system.

---

## 1. System Access & Credentials

- **Frontend URL:** `http://localhost:5173/`
- **Backend API:** `http://127.0.0.1:8000`
- **Default Administrator Credentials:**
  - **Email:** `admin@example.test` (or configured via `ADMIN_EMAIL`)
  - **Password:** Configured via `ADMIN_PASSWORD` in `backend/.env` (provisioned during setup / seed)

---

## 2. Complete Step-by-Step Navigation Flow

```
[Sign In] 
   └──> [Overview] 
           └──> [Agents & Tools] ──> [Policies] ──> [Demo Playground] ──> [Approvals] ──> [Audit]
                                                                                │
                                                                       [AI Copilot Switcher]
```

---

### Step 1: Sign In & Workspace Dashboard
1. Navigate to `http://localhost:5173/`.
2. Enter the administrator credentials:
   - Email: `admin@example.test`
   - Password: `Admin@Hackathon2026!`
3. Click **Sign in**.
4. You land on the **Overview** dashboard:
   - **Metrics Bar:** Displays Active Policy status, count of Agents, Pending Approvals, and Connectors.
   - **Governance Workflow Guide:** Quick-jump buttons to each section of the workflow.
   - **Tier Guide:** Real-time visibility into the 4-tier governor checks (Tier 0 Scope/Policy, Tier 1 Risk Assessment, Tier 2 Semantic Review, Tier 3 Dual-Control Review & Audit).

---

### Step 2: Agents & Tools (Paired Setup Modules)
In the left sidebar, click **Agents & Tools**. Each section features paired side-by-side modules so you see immediate results without scrolling:

#### A. Supported Resources
1. In **1. Connect supported resource** (left):
   - **Display name:** `Sales Database` | **Connector type:** `Demo sales database` &rarr; click **Connect resource**.
   - **Display name:** `Report Storage` | **Connector type:** `Protected report artifacts` &rarr; click **Connect resource**.
   - **Display name:** `Delivery Outbox` | **Connector type:** `Simulated delivery only` &rarr; click **Connect resource**.
2. Notice the live cards appearing on the right under **Connected resources (3)**:
   - Click **Test connection** on any card. The output displays **inline directly inside that card** with a Close button.

#### B. Register Agent & Key Generation
1. In **2. Register an agent** (left):
   - **Agent name:** `Financial Analyst Agent`
   - **Business role:** `data_analyst`
   - Click **Register agent**.
2. Under **Registered agents (1)** (right), click **Generate key**:
   - The secret API key banner appears **inline directly inside that agent's card**.
   - Copy the key and click **I have saved it securely**.

#### C. Reviewer Group & Scoped Task
1. In **3. Create reviewer group**:
   - Group name: `Security Reviewers` &rarr; click **Create group**.
2. In **4. Create a scoped task**:
   - Task name: `sales-report`
   - Permitted business roles: `data_analyst`
   - **Resources:** Select `Sales Database`, `Report Storage`, and `Delivery Outbox` (hold `Ctrl` or `Cmd` to select all 3).
   - **Assigned agents:** Select `Financial Analyst Agent`.
   - Click **Create task**.
   - *Result:* Task appears on the right under **Task assignments (1)**.

---

### Step 3: Policies (Upload, Suggest, Validate, Publish)
In the left sidebar, click **Policies**:

1. Under **Upload company policy**:
   - Upload `hackathon_starter_kit/samples/sales_policy.md` (or `backend/data/sample_policies/company_policy.md`).
   - Click **Upload source**.
2. Under **Propose rules without a cloud model**:
   - Source: `sales_policy.md`
   - Task: `sales-report`
   - Business role: `data_analyst`
   - Reviewer group: `Security Reviewers`
   - Click **Generate draft suggestions**.
3. **Structured Rules Review (Human-in-the-Loop Governance):**
   - The generated rules appear in the **Structured rules** editor.
   - *Important:* The compiler flags assumptions to ensure human verification. In the editor, ensure `"assumptions": []` is empty for all 3 rules.
4. **Publish in One Click:**
   - Click **Publish validated policy** (or click **Validate saved draft** first).
   - The policy updates to **`PUBLISHED`** and is now active workspace-wide.

---

### Step 4: Demo Playground (Governed Workflow Execution)
In the left sidebar, click **Demo Playground**:

1. **Action 1 — Read Sales Data:**
   - Agent: `Financial Analyst Agent`
   - Assigned task: `sales-report`
   - Action: `1. Read sales data` (`database.read`)
   - Task resource: `Sales Database`
   - Maximum rows: `3`
   - Click **Submit governed action**.
   - *Result:* Decision is `ALLOW`. Tier 0-3 results display. A 1-click button appears:  
     `[Use this data to create a report]`.

2. **Action 2 — Create Report:**
   - Click **Use this data to create a report**. The form automatically switches to `2. Create a report` (`report.create`) with the source artifact ID populated.
   - Task resource: `Report Storage`
   - Click **Submit governed action**.
   - *Result:* Report is created. A 1-click button appears:  
     `[Use this report for simulated delivery]`.

3. **Action 3 — Propose Report Delivery (Escalation Trigger):**
   - Click **Use this report for simulated delivery**. The form automatically switches to `3. Propose report delivery` (`report.send`).
   - Task resource: `Delivery Outbox`
   - Simulated recipient: `review@example.test`
   - Click **Submit governed action**.
   - *Result:* Flagged as high impact (`ESCALATE`), state sets to `REVIEW_REQUIRED`, requiring a separate human reviewer.

---

### Step 5: Approvals (Dual-Control Review)
In the left sidebar, click **Approvals**:
1. Pending escalation requests matching your reviewer groups appear here.
2. Note on Separation of Duties: An action initiator cannot approve their own escalation. A different authorized member from `Security Reviewers` can approve or reject the action.
3. Upon approval, the governor revalidates the exact action and completes simulated delivery to the outbox.

---

### Step 6: Audit & Tamper-Evident Ledger
In the left sidebar, click **Audit**:
1. **Verify Hash Chain:** Click **Verify chain** to cryptographically verify the SHA-256 ledger integrity.
2. **Export Checkpoint:** Click **Export checkpoint** to copy the head hash and event count for off-site retention and drift detection.

---

### Step 7: AI Copilot Mode Switcher (Pinecone RAG)
1. At the bottom of the sidebar, click **AI Copilot (Pinecone) &rarr;** (or visit `http://localhost:5173/?legacy=1`).
2. Interact with the multi-provider LLM failover cascade (Groq &rarr; Gemini) and Pinecone vector retrieval.
3. To return, click **&larr; Switch to PNG5 Governor Workspace** at the top of the screen.
