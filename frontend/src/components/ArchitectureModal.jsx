import React, { useEffect, useRef } from 'react';

export default function ArchitectureModal({
  isOpen,
  onClose,
  systemStatus = 'ONLINE',
  statusDetail = 'All Systems Operational',
  subsystems = null
}) {
  const modalRef = useRef(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      modalRef.current?.focus();
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Real diagnostics derived directly from /ready endpoint
  const isOnline = systemStatus !== 'OFFLINE';
  const dbConnected = subsystems?.database?.status === 'connected';
  const dbDegraded = subsystems?.database?.status === 'degraded' || subsystems?.database?.detail?.includes('sqlite');
  const vectorConnected = subsystems?.vector_store?.status === 'connected';
  const vectorMock = subsystems?.vector_store?.status === 'fallback_mock';
  const groqConfigured = subsystems?.ai_providers?.groq === 'configured';
  const geminiConfigured = subsystems?.ai_providers?.gemini === 'configured';
  const llmOnline = groqConfigured || geminiConfigured;

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="architecture-modal-title"
    >
      <div className="glass-card architecture-modal-card" ref={modalRef} tabIndex="-1">
        <div className="card-header flex-between">
          <div>
            <div className={`badge-pill ${isOnline ? 'online' : 'offline'}`} style={{ marginBottom: '0.4rem' }}>
              System Status: {systemStatus} ({statusDetail})
            </div>
            <h2 id="architecture-modal-title" className="card-title">
              ⚡ CODE_STORM End-to-End System Topology
            </h2>
            <p className="card-subtitle">
              Production-hardened GenAI architecture with zero-trust input scanning, dual-engine failover, and dual-layer data persistence.
            </p>
          </div>
          <button
            type="button"
            className="secondary-btn btn-sm"
            onClick={onClose}
            aria-label="Close architecture modal"
          >
            ✕ Close
          </button>
        </div>

        {/* Live Subsystem Diagnostics: Gateway, Pinecone, PostgreSQL, LLM, Security */}
        <div className="arch-status-strip" role="region" aria-label="Live subsystem health">
          <div className="arch-status-item">
            <span className={`arch-dot ${isOnline ? 'online' : 'offline'}`}></span>
            <span>Gateway: <strong>{isOnline ? 'Operational' : 'Unavailable'}</strong></span>
          </div>
          <div className="arch-status-item">
            <span className={`arch-dot ${vectorConnected ? 'online' : (vectorMock ? 'degraded' : 'offline')}`}></span>
            <span>Pinecone: <strong>{vectorConnected ? 'Operational' : (vectorMock ? 'Degraded (Fallback)' : 'Unavailable')}</strong></span>
          </div>
          <div className="arch-status-item">
            <span className={`arch-dot ${dbConnected ? 'online' : (dbDegraded ? 'degraded' : 'offline')}`}></span>
            <span>PostgreSQL: <strong>{dbConnected ? 'Operational' : (dbDegraded ? 'Degraded (SQLite)' : 'Unavailable')}</strong></span>
          </div>
          <div className="arch-status-item">
            <span className={`arch-dot ${llmOnline ? 'online' : 'offline'}`}></span>
            <span>LLM: <strong>{llmOnline ? 'Operational' : 'Unavailable'}</strong></span>
          </div>
          <div className="arch-status-item">
            <span className={`arch-dot ${isOnline ? 'online' : 'offline'}`}></span>
            <span>Security: <strong>{isOnline ? 'Operational' : 'Unavailable'}</strong></span>
          </div>
        </div>

        {/* 10-Second Visual Data Flow Pipeline */}
        <div className="arch-flow-container" role="region" aria-label="System data flow pipeline">
          {/* Layer 1: Client */}
          <div className="arch-layer">
            <div className="arch-layer-title">Layer 1 &bull; Presentation & Client</div>
            <div className="arch-node-box primary-node">
              <div className="node-icon">💻</div>
              <div className="node-title">React 19 + Vite Frontend</div>
              <div className="node-sub">Accessible UI • Responsive 320px–1920px • Realtime Toast & Fault-Tolerant ErrorBoundary</div>
            </div>
          </div>

          <div className="arch-connector-arrow">&darr; HTTPS POST / JSON (With X-Request-ID Correlation)</div>

          {/* Layer 2: API Gateway & Security */}
          <div className="arch-layer">
            <div className="arch-layer-title">Layer 2 &bull; API Gateway & Security Enforcement</div>
            <div className="arch-grid-2">
              <div className="arch-node-box">
                <div className="node-icon">⚡</div>
                <div className="node-title">FastAPI Backend Engine</div>
                <div className="node-sub">RequestID Middleware • CORS Guard • Asyncpg Connection Pool</div>
              </div>
              <div className="arch-node-box security-node">
                <div className="node-icon">🛡️</div>
                <div className="node-title">Tier 0 Deterministic Security Scaffold</div>
                <div className="node-sub">Pre-Inference Regex Scanner • Intercepts Prompt Injection Before Vector Retrieval</div>
              </div>
            </div>
          </div>

          <div className="arch-connector-arrow">&darr; Verified Clean Request Dispatched</div>

          {/* Layer 3: Vector Knowledge & Extraction Engine */}
          <div className="arch-layer">
            <div className="arch-layer-title">Layer 3 &bull; Grounded Knowledge & Structured Extraction</div>
            <div className="arch-grid-2">
              <div className="arch-node-box">
                <div className="node-icon">🌲</div>
                <div className="node-title">Pinecone Vector RAG</div>
                <div className="node-sub">Cosine Similarity Retrieval • 1024-dim Normalized Embeddings • Source Chunk Attribution</div>
              </div>
              <div className="arch-node-box">
                <div className="node-icon">📐</div>
                <div className="node-title">Pydantic v2 Extraction</div>
                <div className="node-sub">Strict Schema Type Enforcement • Automated 1-Attempt Feedback Correction</div>
              </div>
            </div>
          </div>

          <div className="arch-connector-arrow">&darr; Context-Augmented Prompt Payload</div>

          {/* Layer 4: Resilient LLM Cascade */}
          <div className="arch-layer">
            <div className="arch-layer-title">Layer 4 &bull; Resilient Multi-Cloud LLM Cascade</div>
            <div className="arch-cascade-box">
              <div className="cascade-step primary-cascade">
                <span className="step-tag">PRIMARY (Ultra-Fast)</span>
                <strong>Groq Cloud</strong>
                <span className="model-spec">llama-3.3-70b-versatile</span>
              </div>
              <div className="cascade-arrow">&rarr; On Timeout / 429 / Exhaustion &rarr;</div>
              <div className="cascade-step fallback-cascade">
                <span className="step-tag">FALLBACK (Resilient)</span>
                <strong>Google Gemini</strong>
                <span className="model-spec">gemini-2.5-flash</span>
              </div>
            </div>
          </div>

          <div className="arch-connector-arrow">&darr; State Synchronization & Audit Logging</div>

          {/* Layer 5: Data Storage */}
          <div className="arch-layer">
            <div className="arch-layer-title">Layer 5 &bull; Enterprise Data Persistence</div>
            <div className="arch-node-box db-node">
              <div className="node-icon">🐘</div>
              <div className="node-title">Aiven PostgreSQL Database (SSL Encrypted)</div>
              <div className="node-sub">Document Catalog • SHA-256 Deduplication • Conversation History • Audit Events</div>
            </div>
          </div>
        </div>

        <div className="arch-modal-footer">
          <p className="arch-footer-note">
            🔒 <strong>Enterprise Trust:</strong> Zero server secrets are exposed to the frontend. All API interactions carry traceable <code>X-Request-ID</code> correlation headers.
          </p>
        </div>
      </div>
    </div>
  );
}
