import {requestJSON, RequestError, safeStorage} from '../workspaceClient';
export {RequestError as ApiError};
const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '';
export function apiClient(endpoint, options = {}) {
  const token = safeStorage.get('png5_token');
  const headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
  return requestJSON(API_BASE_URL + endpoint, {timeoutMs:35000, ...options, headers});
}
