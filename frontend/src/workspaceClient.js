/** Shared transport: deadline covers headers AND body; writes are never auto-retried. */
export class RequestError extends Error {
  constructor(message, { status = 0, code = 'NETWORK_ERROR', requestId = null, uncertain = false } = {}) {
    super(message); this.name = 'RequestError'; Object.assign(this, { status, code, requestId, uncertain });
  }
}
export const isCancelled = error => ['CANCELLED', 'STALE_REQUEST'].includes(error?.code);
export function describeError(error) {
  const message = error instanceof SyntaxError ? 'Invalid JSON. Check the editor and try again.' : error?.message || 'Something went wrong. Your input has been kept.';
  return `${message}${error?.requestId ? ` Request ID: ${error.requestId}.` : ''}${error?.uncertain ? ' The server may have completed this operation. Refresh its status before submitting again.' : ''}`;
}
export async function requestJSON(url, { token, body, method = 'GET', fetcher = fetch, signal, timeoutMs = 30000, headers = {} } = {}) {
  const controller = new AbortController();
  const write = !['GET', 'HEAD'].includes(method.toUpperCase());
  let timedOut = false, dispatched = false, rejectAbort;
  const abort = () => controller.abort();
  const aborted = new Promise((_, reject) => { rejectAbort = reject; });
  // Promise race also bounds body reading and test transports that ignore AbortSignal.
  controller.signal.addEventListener('abort', () => rejectAbort(new RequestError(
    timedOut ? 'The request took too long.' : 'Request cancelled.',
    { code: timedOut ? 'REQUEST_TIMEOUT' : 'CANCELLED', uncertain: write && dispatched },
  )), { once: true });
  const timer = setTimeout(() => { timedOut = true; abort(); }, timeoutMs);
  signal?.addEventListener('abort', abort, { once: true });
  if (signal?.aborted) abort();
  const run = async () => {
    if (controller.signal.aborted) return await aborted;
    const multipart = body instanceof FormData;
    const finalHeaders = { ...headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
    if (body !== undefined && body !== null && !multipart) finalHeaders['Content-Type'] ??= 'application/json';
    const encoded = body === undefined || body === null ? undefined : multipart ? body : JSON.stringify(body);
    dispatched = true;
    const response = await fetcher(url, { method, headers: finalHeaders, body: encoded, signal: controller.signal, cache: 'no-store', credentials: 'omit' });
    const requestId = response.headers?.get('x-request-id') || null;
    if (response.status === 204) return null;
    let result;
    try { result = await response.json(); }
    catch {
      throw new RequestError('The server returned an unreadable response.', { status: response.status, code: 'INVALID_RESPONSE', requestId, uncertain: write });
    }
    if (!response.ok) {
      const detail = result?.detail;
      const fallback = {401:'Session expired or credentials invalid. Sign in again.',403:'You do not have permission for this action.',409:'This record changed. Refresh it before trying again.',413:'The upload exceeds the server size limit.',429:'Too many requests. Wait before trying again.'}[response.status] || 'The server could not complete the request.';
      const message = typeof detail === 'string' ? detail : detail?.message || result?.error?.message || fallback;
      throw new RequestError(message, { status: response.status, code: `HTTP_${response.status}`, requestId: detail?.request_id || result?.request_id || requestId,
        uncertain: write && response.status >= 500 });
    }
    if (result === null || typeof result !== 'object') throw new RequestError('Unexpected server response.', {code:'INVALID_RESPONSE', uncertain:write});
    return result;
  };
  try { return await Promise.race([run(), aborted]); }
  catch (error) {
    if (error instanceof RequestError || error instanceof SyntaxError) throw error;
    throw new RequestError('Unable to reach the backend. Check your connection and server.', { uncertain: write && dispatched });
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}
export function request(path, options) { return requestJSON(`/api${path}`, options); }
export function parseRules(text) {
  let rules;
  try { rules = JSON.parse(text); } catch { return { rules: [], error: 'Rules must be valid JSON.' }; }
  if (!Array.isArray(rules) || rules.some(r => !r || typeof r !== 'object' || Array.isArray(r) || typeof r.id !== 'string' || !r.id.trim())) {
    return { rules: [], error: 'Rules must be an array of objects, each with a rule ID.' };
  }
  if (new Set(rules.map(r => r.id)).size !== rules.length) return { rules: [], error: 'Each rule ID must be unique.' };
  return { rules, error: '' };
}
export function diffRules(previous = [], next = []) {
  const entries = rows => (Array.isArray(rows) ? rows : []).filter(r => r && typeof r.id === 'string').map(r => [r.id, r]);
  const before = new Map(entries(previous)), after = new Map(entries(next));
  return [...new Set([...before.keys(), ...after.keys()])].map(id => ({id,before:before.get(id),after:after.get(id),status:!before.has(id)?'Added':!after.has(id)?'Removed':JSON.stringify(before.get(id))===JSON.stringify(after.get(id))?'Unchanged':'Changed'}));
}
export const mayPublish = (policy, permissions) => policy?.state === 'VALIDATED' && permissions.includes('publish');
export const mayReview = (action, id) => action.state === 'REVIEW_REQUIRED' && action.initiated_by !== id && action.agent_id !== id && (!action.expires_at || action.expires_at * 1000 > Date.now());
export const safeStorage = {
  get(key) { try { return sessionStorage.getItem(key) || ''; } catch { return ''; } },
  set(key, value) { try { if (value) sessionStorage.setItem(key, value); else sessionStorage.removeItem(key); } catch { /* Storage disabled: current in-memory session still works. */ } },
};
