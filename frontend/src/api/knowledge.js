import { apiClient } from './client';

export async function getRagStats(signal) {
  return apiClient('/api/rag/stats', {signal});
}

export async function reindexKnowledge(signal) {
  return apiClient('/api/rag/reindex', {
    signal, method: 'POST'
  });
}

export async function queryRag(query, topK = 4, minScore = 0.3, signal) {
  return apiClient('/api/rag/query', {
    signal, method: 'POST',
    body: {
      query,
      top_k: topK,
      min_score: minScore
    }
  });
}

export async function listDocuments(signal) {
  return apiClient('/api/documents', {signal});
}

export async function uploadDocument(file, signal) {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient('/api/documents', {
    signal, method: 'POST',
    body: formData
  });
}

export async function deleteDocument(docId, signal) {
  return apiClient(`/api/documents/${docId}`, {
    signal, method: 'DELETE'
  });
}
