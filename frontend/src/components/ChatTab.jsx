import React, { useState, useRef, useEffect } from 'react';
import { processQuery } from '../api/chat';

const QUICK_PROMPTS = [
  "What is the CODE_STORM target architecture?",
  "How does the Groq to Gemini LLM failover cascade work?",
  "Explain Pinecone vector retrieval and document deduplication.",
  "What are the hackathon presentation best practices?"
];

export default function ChatTab() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Welcome to the CODE_STORM AI Copilot. Ask any question regarding system architecture, hackathon guidelines, or domain policies.',
      provider: 'System',
      sources: [],
      groundedSources: []
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (queryText = null) => {
    const textToSend = (typeof queryText === 'string' ? queryText : inputQuery).trim();
    if (!textToSend || isLoading) return;

    setInputQuery('');
    setErrorMessage('');
    setMessages((prev) => [...prev, { role: 'user', content: textToSend }]);
    setIsLoading(true);

    try {
      const data = await processQuery(textToSend, '', conversationId);

      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          provider: data.provider_used,
          sources: data.sources || [],
          groundedSources: data.grounded_sources || []
        }
      ]);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to process request.');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error: ${err.message}`,
          provider: 'Error',
          sources: [],
          groundedSources: [],
          isError: true,
          requestId: err.requestId
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'Conversation cleared. How can I help you next?',
        provider: 'System',
        sources: [],
        groundedSources: []
      }
    ]);
    setConversationId(null);
    setErrorMessage('');
  };

  return (
    <div className="glass-card">
      <div className="card-header flex-between">
        <div>
          <h2 className="card-title">💬 Grounded AI Domain Copilot</h2>
          <p className="card-subtitle">
            Pinecone semantic vector retrieval with Tier 0 security scan and resilient Groq/Gemini LLM failover.
          </p>
        </div>
        <button
          className="secondary-btn btn-sm"
          onClick={handleClearChat}
          title="Start a new chat session"
        >
          🗑️ Clear
        </button>
      </div>

      <div className="chat-window">
        <div className="messages-list">
          {messages.map((m, idx) => (
            <div key={idx} className={`message-bubble ${m.role} ${m.isError ? 'error-bubble' : ''}`}>
              <div className="bubble-content">{m.content}</div>

              {m.role === 'assistant' && (
                <div className="bubble-meta">
                  <div className="provider-pill">
                    ⚡ <strong>{m.provider}</strong>
                    {m.requestId && <span className="req-id"> (Ref: {m.requestId.slice(0, 8)})</span>}
                  </div>

                  {m.groundedSources && m.groundedSources.length > 0 && (
                    <div className="sources-container">
                      <span className="sources-label">Verified Sources:</span>
                      <div className="sources-tags">
                        {m.groundedSources.map((s, sIdx) => (
                          <span
                            key={sIdx}
                            className="source-tag"
                            title={`Chunk ${s.chunk_id} | Section: ${s.section} | Score: ${(s.score * 100).toFixed(1)}%`}
                          >
                            📄 {s.document_name} ({Math.round(s.score * 100)}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="message-bubble assistant loading-bubble">
              <span className="spinner-dots"></span> Searching Pinecone vector index & synthesizing grounded answer...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick prompt suggestions */}
        <div className="quick-prompts">
          {QUICK_PROMPTS.map((prompt, pIdx) => (
            <button
              key={pIdx}
              className="prompt-chip"
              onClick={() => handleSend(prompt)}
              disabled={isLoading}
            >
              {prompt}
            </button>
          ))}
        </div>

        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="chat-input-area">
          <input
            type="text"
            className="chat-input"
            placeholder="Ask a question or enter a task prompt..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="primary-btn"
            disabled={isLoading || !inputQuery.trim()}
          >
            {isLoading ? 'Thinking...' : 'Send ➜'}
          </button>
        </form>

        {errorMessage && (
          <div className="error-banner">
            ⚠️ {errorMessage}
          </div>
        )}
      </div>
    </div>
  );
}
