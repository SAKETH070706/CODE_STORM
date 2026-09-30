/**
 * Centralized API Client for CODE_STORM Platform
 * Eliminates hardcoded localhost URLs and provides unified error handling,
 * request tracing, and timeout management.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(message, status = 0, code = 'NETWORK_ERROR', details = null, requestId = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

/**
 * Standard HTTP request wrapper with timeout, CORS and error handling.
 */
export async function apiClient(endpoint, {
  method = 'GET',
  body = null,
  headers = {},
  timeoutMs = 35000,
  signal = null
} = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Link caller's abort signal if supplied
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  const finalHeaders = { ...headers };
  const isFormData = body instanceof FormData;

  if (!isFormData && !finalHeaders['Content-Type'] && method !== 'GET') {
    finalHeaders['Content-Type'] = 'application/json';
  }

  let finalBody = body;
  if (!isFormData && body && typeof body === 'object') {
    finalBody = JSON.stringify(body);
  }

  try {
    const res = await fetch(url, {
      method,
      headers: finalHeaders,
      body: finalBody,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    const requestId = res.headers.get('X-Request-ID') || res.headers.get('x-request-id');
    const contentType = res.headers.get('content-type') || '';
    let data = null;

    if (contentType.includes('application/json')) {
      data = await res.json().catch(() => null);
    } else {
      const text = await res.text().catch(() => '');
      data = { raw: text };
    }

    if (!res.ok) {
      let message = 'An unexpected server error occurred.';
      let code = `HTTP_${res.status}`;
      let details = null;

      if (data?.error) {
        message = data.error.message || message;
        code = data.error.code || code;
        details = data.error.details;
      } else if (data?.detail) {
        message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }

      // Friendly mapping for common HTTP status codes
      if (res.status === 400) code = 'BAD_REQUEST';
      else if (res.status === 401) message = 'Authentication required.';
      else if (res.status === 403) message = 'Access denied / Insufficient permissions.';
      else if (res.status === 404) message = 'The requested resource was not found.';
      else if (res.status === 408) message = 'Request timed out waiting for server response.';
      else if (res.status === 413) message = 'Uploaded file exceeds the maximum size limit.';
      else if (res.status === 429) message = 'Rate limit exceeded. Please wait a moment.';
      else if (res.status === 502 || res.status === 503) message = 'Backend AI service or database temporarily unavailable.';
      else if (res.status === 504) message = 'Gateway timeout: AI provider took too long to answer.';

      throw new ApiError(message, res.status, code, details, requestId);
    }

    return data;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out. Please verify the backend is running.', 408, 'REQUEST_TIMEOUT');
    }
    // Failed to fetch typically means network or CORS issue
    throw new ApiError(
      'Unable to connect to FastAPI backend. Check that the backend server is running and CORS is configured.',
      0,
      'NETWORK_FAILURE'
    );
  }
}
