import { apiClient } from './client';

export async function processQuery(query, userContext = '', conversationId = null) {
  return apiClient('/api/process', {
    method: 'POST',
    body: {
      query,
      user_context: userContext,
      conversation_id: conversationId
    }
  });
}

export async function listConversations() {
  return apiClient('/api/conversations');
}

export async function getConversationMessages(conversationId) {
  return apiClient(`/api/conversations/${conversationId}/messages`);
}
