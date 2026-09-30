import { apiClient } from './client';

export async function getRagStats() {
  return apiClient('/api/rag/stats');
}

export async function reindexKnowledge() {
  return apiClient('/api/rag/reindex', {
    method: 'POST'
  });
}

export async function queryRag(query, topK = 4, minScore = 0.3) {
  return apiClient('/api/rag/query', {
    method: 'POST',
    body: {
      query,
      top_k: topK,
      min_score: minScore
    }
  });
}

export async function listDocuments() {
  return apiClient('/api/documents');
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient('/api/documents', {
    method: 'POST',
    body: formData
  });
}

export async function deleteDocument(docId) {
  return apiClient(`/api/documents/${docId}`, {
    method: 'DELETE'
  });
}
