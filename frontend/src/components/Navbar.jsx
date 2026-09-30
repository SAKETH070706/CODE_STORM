import React, { useEffect, useState, useRef } from 'react';

export default function Navbar({
  activeTab,
  onNavigate,
  onOpenArchitecture,
  systemStatus = 'CHECKING',
  statusDetail = 'Connecting to backend...'
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef(null);
  const hamburgerBtnRef = useRef(null);

  // Close mobile menu on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
        hamburgerBtnRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileMenuOpen]);

  // Close mobile menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        isMobileMenuOpen &&
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(e.target) &&
        !hamburgerBtnRef.current.contains(e.target)
      ) {
        setIsMobileMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isMobileMenuOpen]);

  const getStatusColorClass = () => {
    if (systemStatus === 'ONLINE') return 'online';
    if (systemStatus === 'DEGRADED') return 'degraded';
    if (systemStatus === 'OFFLINE') return 'offline';
    return 'checking';
  };

  const handleNavClick = (tabKey) => {
    if (onNavigate) onNavigate(tabKey);
    setIsMobileMenuOpen(false);
  };

  const handleArchClick = () => {
    if (onOpenArchitecture) onOpenArchitecture();
    setIsMobileMenuOpen(false);
  };

  return (
    <header className="navbar" role="banner">
      <div className="navbar-top-row">
        {/* Clickable Brand / Logo */}
        <button
          type="button"
          className="brand-btn"
          onClick={() => handleNavClick('chat')}
          title="Return to CODE_STORM Home (AI Copilot)"
          aria-label="CODE_STORM Home"
        >
          <div className="brand">
            <div className="brand-icon" aria-hidden="true">⚡</div>
            <div className="brand-text">
              <div className="brand-logo">CODE_STORM</div>
              <div className="brand-tag">Production GenAI Platform</div>
            </div>
          </div>
        </button>

        {/* Desktop Badges & Architecture Modal Trigger */}
        <div className="nav-badges desktop-badges" role="region" aria-label="System status and active providers">
          <div className="model-pill" title="Primary High-Speed LLM Inference">
            Groq: <span>llama-3.3-70b</span>
          </div>
          <div className="model-pill" title="Resilient Fallback LLM Inference">
            Gemini: <span>2.5-flash</span>
          </div>
          <div className="model-pill" title="Vector Database">
            Vector: <span>Pinecone</span>
          </div>

          <button
            type="button"
            className="arch-nav-btn"
            onClick={handleArchClick}
            title="Inspect end-to-end system architecture & data flow"
          >
            📊 Architecture
          </button>

          <div className="status-badge" title={statusDetail} role="status">
            <span className={`status-dot ${getStatusColorClass()}`} aria-hidden="true"></span>
            <span className="status-text">{systemStatus}</span>
          </div>
        </div>

        {/* Mobile Hamburger Button */}
        <button
          ref={hamburgerBtnRef}
          type="button"
          className="hamburger-btn"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-expanded={isMobileMenuOpen}
          aria-label="Toggle navigation menu"
          aria-controls="mobile-navigation-menu"
        >
          <span className={`hamburger-bar ${isMobileMenuOpen ? 'open' : ''}`}></span>
          <span className={`hamburger-bar ${isMobileMenuOpen ? 'open' : ''}`}></span>
          <span className={`hamburger-bar ${isMobileMenuOpen ? 'open' : ''}`}></span>
        </button>
      </div>

      {/* Mobile Drawer Navigation */}
      {isMobileMenuOpen && (
        <div
          id="mobile-navigation-menu"
          ref={mobileMenuRef}
          className="mobile-menu-drawer"
          role="navigation"
          aria-label="Mobile Navigation"
        >
          <div className="mobile-menu-links">
            <button
              type="button"
              className={`mobile-menu-item ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => handleNavClick('chat')}
            >
              💬 AI Copilot (Pinecone RAG)
            </button>
            <button
              type="button"
              className={`mobile-menu-item ${activeTab === 'extract' ? 'active' : ''}`}
              onClick={() => handleNavClick('extract')}
            >
              📷 Multimodal Extraction
            </button>
            <button
              type="button"
              className={`mobile-menu-item ${activeTab === 'knowledge' ? 'active' : ''}`}
              onClick={() => handleNavClick('knowledge')}
            >
              📚 Vector Knowledge
            </button>
            <button
              type="button"
              className="mobile-menu-item arch-mobile-item"
              onClick={handleArchClick}
            >
              📊 Inspect System Architecture
            </button>
          </div>

          <div className="mobile-menu-status">
            <div className="status-badge" title={statusDetail}>
              <span className={`status-dot ${getStatusColorClass()}`} aria-hidden="true"></span>
              <span className="status-text">{systemStatus}: {statusDetail}</span>
            </div>
            <div className="mobile-model-pills">
              <span className="model-pill">Groq 70B</span>
              <span className="model-pill">Gemini 2.5</span>
              <span className="model-pill">Pinecone</span>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
