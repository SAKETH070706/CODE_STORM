import React from 'react';

export default function NotFoundPage({ onNavigate }) {
  return (
    <div className="glass-card not-found-card" role="region" aria-label="Page Not Found">
      <div className="not-found-content">
        <div className="not-found-code">404</div>
        <h2 className="card-title">Requested View Not Found</h2>
        <p className="card-subtitle not-found-desc">
          The requested section, route, or resource is not available. Please return to the primary AI Copilot or select a valid workspace module below.
        </p>

        <div className="not-found-actions">
          <button
            type="button"
            className="primary-btn"
            onClick={() => onNavigate('chat')}
          >
            💬 Return to AI Copilot
          </button>
          <button
            type="button"
            className="secondary-btn"
            onClick={() => onNavigate('extract')}
          >
            📷 Multimodal Extraction
          </button>
          <button
            type="button"
            className="secondary-btn"
            onClick={() => onNavigate('knowledge')}
          >
            📚 Vector Knowledge
          </button>
        </div>
      </div>
    </div>
  );
}
