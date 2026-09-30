import { apiClient } from './client';

export async function checkHealth() {
  return apiClient('/health', { timeoutMs: 5000 });
}

export async function checkReadiness() {
  return apiClient('/ready', { timeoutMs: 5000 });
}
