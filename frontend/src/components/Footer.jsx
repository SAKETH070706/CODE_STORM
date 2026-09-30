import React from 'react';

const CURRENT_YEAR = new Date().getFullYear();

export default function Footer({ onNavigate, activeTab }) {

  return (
    <footer className="app-footer" role="contentinfo" aria-label="Site Footer">
      <div className="footer-grid">
        {/* Brand Column */}
        <div className="footer-col brand-col">
          <div className="footer-brand">
            <span className="brand-icon-sm" aria-hidden="true">⚡</span>
            <span className="footer-brand-title">CODE_STORM</span>
          </div>
          <p className="footer-desc">
            Production-grade GenAI intelligence platform powered by Pinecone semantic retrieval, Aiven PostgreSQL, and dual-engine Groq/Gemini LLM orchestration.
          </p>
          <div className="footer-stack-badges">
            <span className="badge-micro">FastAPI</span>
            <span className="badge-micro">PostgreSQL</span>
            <span className="badge-micro">Pinecone</span>
            <span className="badge-micro">Groq 70B</span>
            <span className="badge-micro">Gemini 2.5</span>
          </div>
        </div>

        {/* Navigation Links Column */}
        <div className="footer-col">
          <h4 className="footer-col-title">Platform Features</h4>
          <ul className="footer-links-list">
            <li>
              <button
                type="button"
                className={`footer-link-btn ${activeTab === 'chat' ? 'active' : ''}`}
                onClick={() => onNavigate('chat')}
              >
                AI Domain Copilot (RAG)
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`footer-link-btn ${activeTab === 'extract' ? 'active' : ''}`}
                onClick={() => onNavigate('extract')}
              >
                Multimodal Structured Extraction
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`footer-link-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
                onClick={() => onNavigate('knowledge')}
              >
                Vector Knowledge & Database
              </button>
            </li>
          </ul>
        </div>

        {/* Developer & API Links Column */}
        <div className="footer-col">
          <h4 className="footer-col-title">Developer & APIs</h4>
          <ul className="footer-links-list">
            <li>
              <a
                href="/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="footer-anchor"
                title="FastAPI Interactive OpenAPI / Swagger Documentation"
              >
                FastAPI Swagger Docs ↗
              </a>
            </li>
            <li>
              <a
                href="/ready"
                target="_blank"
                rel="noopener noreferrer"
                className="footer-anchor"
                title="Realtime System Readiness & Dependency Health"
              >
                Health & Readiness API ↗
              </a>
            </li>
            <li>
              <a
                href="https://github.com/SAKETH070706/CODE_STORM"
                target="_blank"
                rel="noopener noreferrer"
                className="footer-anchor"
                title="GitHub Repository"
              >
                GitHub Source Code ↗
              </a>
            </li>
          </ul>
        </div>

        {/* Contact & Support Column */}
        <div className="footer-col">
          <h4 className="footer-col-title">Support & Contact</h4>
          <ul className="footer-links-list">
            <li>
              <a
                href="mailto:support@codestorm.ai"
                className="footer-anchor"
                title="Send email to support"
              >
                ✉️ support@codestorm.ai
              </a>
            </li>
            <li>
              <a
                href="tel:+18005550199"
                className="footer-anchor"
                title="Call technical helpline"
              >
                📞 +1 (800) 555-0199
              </a>
            </li>
            <li className="footer-text-muted">
              Response SLA: &lt; 15 mins during hackathon
            </li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <p className="copyright-text">
          &copy; {CURRENT_YEAR} CODE_STORM GenAI Platform. All rights reserved.
        </p>
        <div className="footer-legal-links">
          <span className="legal-item">Production Hardened</span>
          <span className="footer-dot">•</span>
          <span className="legal-item">SOC2 Type II Ready</span>
          <span className="footer-dot">•</span>
          <span className="legal-item">Zero Data Retention</span>
        </div>
      </div>
    </footer>
  );
}
