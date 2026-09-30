import { apiClient } from './client';

export async function extractText(text) {
  return apiClient('/api/extract', {
    method: 'POST',
    body: { text }
  });
}

export async function extractImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient('/api/extract/image', {
    method: 'POST',
    body: formData
  });
}
