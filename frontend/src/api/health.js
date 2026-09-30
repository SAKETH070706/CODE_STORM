import { apiClient } from './client';

export async function checkHealth(signal) {
  return apiClient('/health', { timeoutMs: 5000, signal });
}

export async function checkReadiness(signal) {
  return apiClient('/ready', { timeoutMs: 5000, signal });
}
