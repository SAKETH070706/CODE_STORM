export async function request(path, { token, body, method = 'GET', fetcher = fetch } = {}) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const multipart = body instanceof FormData;
  if (body !== undefined && !multipart) headers['Content-Type'] = 'application/json';
  const response = await fetcher(`/api${path}`, {method, headers, body: body === undefined ? undefined : multipart ? body : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
  const result = await response.json().catch(() => ({ detail: 'Unreadable server response' }));
  if (!response.ok) { const error = new Error(typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail)); error.status = response.status; throw error; }
  return result;
}
export function diffRules(previous = [], next = []) {
  const before = new Map(previous.map(r => [r.id, r]));
  const after = new Map(next.map(r => [r.id, r]));
  return [...new Set([...before.keys(), ...after.keys()])].map(id => ({id, before: before.get(id), after: after.get(id), status: !before.has(id) ? 'Added' : !after.has(id) ? 'Removed' : JSON.stringify(before.get(id)) === JSON.stringify(after.get(id)) ? 'Unchanged' : 'Changed'}));
}
export const mayPublish = (policy, permissions) => policy?.state === 'VALIDATED' && permissions.includes('publish');
export const mayReview = (action, id) => action.state === 'REVIEW_REQUIRED' && action.initiated_by !== id && action.agent_id !== id;
