import React from 'react';

export default function HeroBanner({ onOpenArchitecture, onSelectTab }) {
  return (
    <section className="hero-banner" aria-label="Platform Highlights">
      <div className="hero-content">
        <div className="hero-top-badge">
          <span className="hero-dot"></span>
          <span>ENTERPRISE-GRADE GENAI ARCHITECTURE</span>
        </div>
        <h1 className="hero-title">
          Grounded AI Intelligence with Resilient Orchestration
        </h1>
        <p className="hero-subtitle">
          Eliminate model hallucinations and jailbreak vulnerabilities. Ground every interaction in verified Pinecone vector knowledge, enforce Pydantic structured schemas, and guarantee uptime through Groq and Gemini failover cascades.
        </p>

        {/* Feature Pills Strip */}
        <div className="hero-features-grid">
          <button
            type="button"
            className="hero-feature-pill"
            onClick={() => onSelectTab('chat')}
            title="Inspect Pinecone semantic vector retrieval in AI Copilot"
          >
            <span className="pill-icon">🌲</span>
            <div className="pill-text">
              <strong>Pinecone Vector RAG</strong>
              <span>Semantic retrieval & source score attribution</span>
            </div>
          </button>

          <button
            type="button"
            className="hero-feature-pill"
            onClick={() => onSelectTab('extract')}
            title="Inspect Pydantic multimodal structured extraction"
          >
            <span className="pill-icon">📐</span>
            <div className="pill-text">
              <strong>Pydantic v2 Extraction</strong>
              <span>Multimodal text & vision schema validation</span>
            </div>
          </button>

          <button
            type="button"
            className="hero-feature-pill"
            onClick={() => onSelectTab('chat')}
            title="Inspect Tier 0 prompt-injection security guardrails"
          >
            <span className="pill-icon">🛡️</span>
            <div className="pill-text">
              <strong>Tier 0 Security Scaffold</strong>
              <span>Realtime adversarial prompt injection defense</span>
            </div>
          </button>

          <button
            type="button"
            className="hero-feature-pill"
            onClick={onOpenArchitecture}
            title="View Groq 70B to Gemini 2.5 LLM failover topology"
          >
            <span className="pill-icon">🔄</span>
            <div className="pill-text">
              <strong>Dual-Engine LLM Cascade</strong>
              <span>Groq 70B primary &rarr; Gemini 2.5 failover</span>
            </div>
          </button>
        </div>
      </div>
    </section>
  );
}
