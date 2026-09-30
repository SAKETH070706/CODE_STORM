import { apiClient } from './client';

export async function extractText(text, signal) {
  return apiClient('/api/extract', {
    signal, method: 'POST',
    body: { text }
  });
}

export async function extractImage(file, signal) {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient('/api/extract/image', {
    signal, method: 'POST',
    body: formData
  });
}
