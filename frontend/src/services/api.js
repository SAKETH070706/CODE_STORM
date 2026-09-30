const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000'

async function request(path, options = {}) {

  const response = await fetch(
    `${API_BASE}${path}`,
    {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    }
  )

  const text = await response.text()

  let data = {}

  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = {
      detail: text
    }
  }

  if (!response.ok) {
    throw new Error(
      data.detail ||
      data.message ||
      `Request failed (${response.status})`
    )
  }

  return data
}

export const api = {

  baseUrl: API_BASE,

  health: () =>
    request('/health'),

  /*
   * These endpoints will be connected
   * to the real FastAPI gateway in Case 6.
   */

  evaluateAction: (payload) =>
    request('/api/actions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getActions: () =>
    request('/api/actions'),

  getAction: (actionId) =>
    request(
      `/api/actions/${encodeURIComponent(actionId)}`
    ),

  getApprovals: () =>
    request('/api/approvals'),

  approveAction: (approvalId, payload = {}) =>
    request(
      `/api/approvals/${encodeURIComponent(
        approvalId
      )}/approve`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  rejectAction: (approvalId, payload = {}) =>
    request(
      `/api/approvals/${encodeURIComponent(
        approvalId
      )}/reject`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  getAudit: () =>
    request('/api/audit'),

  getPolicies: () =>
    request('/api/policies'),

  ragStats: () =>
    request('/api/rag/stats'),

  ragIngest: () =>
    request('/api/rag/ingest', {
      method: 'POST'
    }),

  processChat: (query) =>
    request('/api/process', {
      method: 'POST',
      body: JSON.stringify({
        query
      }),
    }),

  extractText: (text) =>
    request('/api/extract', {
      method: 'POST',
      body: JSON.stringify({
        text
      }),
    }),

  extractImage: (file) => {

    const formData = new FormData()

    formData.append('file', file)

    return fetch(
      `${API_BASE}/api/extract/image`,
      {
        method: 'POST',
        body: formData,
      }
    ).then(async response => {

      const data =
        await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          data.detail ||
          data.error ||
          `Request failed (${response.status})`
        )
      }

      return data
    })
  }
}