const API_BASE = 'http://localhost:8000';


/* ============================================================
   GENERIC REQUEST
============================================================ */

async function request(path, options = {}) {

    const response = await fetch(
        `${API_BASE}${path}`,
        {
            ...options,

            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {}),
            },
        }
    );


    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }


    if (!response.ok) {

        const message =
            data?.detail ||
            data?.message ||
            `Request failed with status ${response.status}`;

        throw new Error(message);
    }


    return data;
}


/* ============================================================
   HEALTH
============================================================ */

async function getHealth() {

    return request('/health');
}


/* ============================================================
   TEXT → TEXT
============================================================ */

async function processQuery(query) {

    return request(
        '/api/process',
        {
            method: 'POST',

            body: JSON.stringify({
                query: query,
            }),
        }
    );
}


/* ============================================================
   GOVERNED ACTIONS
============================================================ */

async function submitAction(action) {

    return request(
        '/api/actions',
        {
            method: 'POST',

            body: JSON.stringify(action),
        }
    );
}


async function getActions() {

    return request(
        '/api/actions'
    );
}


async function getAction(actionId) {

    return request(
        `/api/actions/${encodeURIComponent(actionId)}`
    );
}


/* ============================================================
   AGENT WORKFLOW
============================================================ */

async function runAgent(task) {

    return request(
        '/api/agent/run',
        {
            method: 'POST',

            body: JSON.stringify(task),
        }
    );
}


/* ============================================================
   APPROVALS
============================================================ */

async function getApprovals() {

    return request(
        '/api/approvals'
    );
}


async function approveAction(
    approvalId,
    reason = 'Approved by dashboard reviewer'
) {

    return request(
        `/api/approvals/${encodeURIComponent(
            approvalId
        )}/approve`,
        {
            method: 'POST',

            body: JSON.stringify({
                reason: reason,
            }),
        }
    );
}


async function rejectAction(
    approvalId,
    reason = 'Rejected by dashboard reviewer'
) {

    return request(
        `/api/approvals/${encodeURIComponent(
            approvalId
        )}/reject`,
        {
            method: 'POST',

            body: JSON.stringify({
                reason: reason,
            }),
        }
    );
}


/* ============================================================
   AUDIT
============================================================ */

async function getAuditEvents() {

    return request(
        '/api/audit'
    );
}


/* ============================================================
   POLICIES
============================================================ */

async function getPolicies() {

    return request(
        '/api/policies'
    );
}


/* ============================================================
   TEXT EXTRACTION
============================================================ */

async function extractText(text) {

    return request(
        '/api/extract',
        {
            method: 'POST',

            body: JSON.stringify({
                text: text,
            }),
        }
    );
}


/* ============================================================
   IMAGE → TEXT
============================================================ */

async function extractImage(file) {

    const formData = new FormData();

    formData.append(
        'file',
        file
    );


    const response = await fetch(
        `${API_BASE}/api/extract/image`,
        {
            method: 'POST',
            body: formData,
        }
    );


    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }


    if (!response.ok) {

        const message =
            data?.detail ||
            data?.message ||
            `Image extraction failed with status ${response.status}`;

        throw new Error(message);
    }


    return data;
}


/* ============================================================
   RAG
============================================================ */

async function getRagStats() {

    return request(
        '/api/rag/stats'
    );
}


async function ingestKnowledge(
    payload = {}
) {

    return request(
        '/api/rag/ingest',
        {
            method: 'POST',

            body: JSON.stringify(payload),
        }
    );
}


/* ============================================================
   CENTRAL API OBJECT
============================================================ */

export const api = {

    /* Health */
    getHealth,

    /* Text → Text */
    processQuery,

    /* Actions */
    submitAction,
    getActions,
    getAction,

    /* Agent */
    runAgent,

    /* Approvals */
    getApprovals,
    approveAction,
    rejectAction,

    /* Audit */
    getAuditEvents,

    /* Policies */
    getPolicies,

    /* Extraction */
    extractText,
    extractImage,

    /* RAG */
    getRagStats,
    ingestKnowledge,

    /* Backward-compatible aliases */
    ragStats: getRagStats,
    ragIngest: ingestKnowledge,
};