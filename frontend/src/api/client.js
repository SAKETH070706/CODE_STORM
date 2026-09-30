import {requestJSON, RequestError} from '../workspaceClient';
export {RequestError as ApiError};
const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '';
export function apiClient(endpoint, options = {}) {
  return requestJSON(API_BASE_URL + endpoint, {timeoutMs:35000,...options});
}
