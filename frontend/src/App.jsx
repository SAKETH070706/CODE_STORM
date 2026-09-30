import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import HeroBanner from './components/HeroBanner';
import ChatTab from './components/ChatTab';
import ExtractTab from './components/ExtractTab';
import KnowledgeTab from './components/KnowledgeTab';
import NotFoundPage from './components/NotFoundPage';
import ArchitectureModal from './components/ArchitectureModal';
import Footer from './components/Footer';
import ErrorBoundary from './components/ErrorBoundary';
import Toast from './components/Toast';
import { checkReadiness, checkHealth } from './api/health';
import './App.css';

const TAB_TITLES = {
  chat: 'AI Copilot (Pinecone RAG) | CODE_STORM',
  extract: 'Multimodal Structured Extraction | CODE_STORM',
  knowledge: 'Vector Knowledge & Database | CODE_STORM',
  '404': '404 - Page Not Found | CODE_STORM'
};

export default function App() {
  // Read initial tab from URL query if present
  const getInitialTab = () => {
    try {
      const params = new URLSearchParams(window.location.search);
      const requested = params.get('tab');
      if (requested) {
        if (['chat', 'extract', 'knowledge'].includes(requested)) {
          return requested;
        }
        return '404';
      }
    } catch (e) {
      console.warn('Could not parse query parameters', e);
    }
    return 'chat';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [toasts, setToasts] = useState([]);
  const [isArchitectureOpen, setIsArchitectureOpen] = useState(false);
  const [systemStatus, setSystemStatus] = useState('CHECKING');
  const [statusDetail, setStatusDetail] = useState('Connecting to backend...');
  const [subsystems, setSubsystems] = useState(null);

  // Poll system readiness & diagnostics
  useEffect(() => {
    let isMounted = true;
    const pollHealth = async () => {
      try {
        const readyData = await checkReadiness();
        if (!isMounted) return;
        setSubsystems(readyData);
        if (readyData.status === 'ready') {
          setSystemStatus('ONLINE');
          setStatusDetail('All Systems Operational');
        } else if (readyData.status === 'degraded') {
          setSystemStatus('DEGRADED');
          const details = [];
          if (readyData.vector_store?.status !== 'connected') details.push('Pinecone (Local Fallback)');
          if (readyData.database?.status !== 'connected') details.push('Database Degraded');
          setStatusDetail(details.length > 0 ? details.join(' | ') : 'Running in Degraded Mode');
        } else {
          setSystemStatus('OFFLINE');
          setStatusDetail('Backend Not Ready');
        }
      } catch (readyErr) {
        if (!isMounted) return;
        console.debug('Readiness check exception:', readyErr?.message);
        try {
          await checkHealth();
          setSystemStatus('DEGRADED');
          setStatusDetail('API Alive (Dependencies Starting)');
        } catch (healthErr) {
          setSystemStatus('OFFLINE');
          setStatusDetail(`Backend Disconnected (${healthErr.message || 'offline'})`);
        }
      }
    };

    pollHealth();
    const interval = setInterval(pollHealth, 7000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Toast notification helper
  const addToast = useCallback((message, type = 'info', duration = 3500) => {
    const id = Date.now() + Math.random().toString(36).slice(2, 6);
    setToasts((prev) => [...prev, { id, message, type }]);
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Update tab & browser URL history
  const handleTabChange = useCallback((tabKey) => {
    setActiveTab(tabKey);
    try {
      const url = new URL(window.location);
      if (tabKey === 'chat') {
        url.searchParams.delete('tab');
      } else {
        url.searchParams.set('tab', tabKey);
      }
      window.history.pushState({}, '', url);
    } catch {
      // Fallback if URL manipulation fails in test environment
    }
  }, []);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get('tab') || 'chat';
      if (['chat', 'extract', 'knowledge'].includes(tab)) {
        setActiveTab(tab);
      } else if (tab) {
        setActiveTab('404');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Sync document title with active tab
  useEffect(() => {
    const title = TAB_TITLES[activeTab] || 'CODE_STORM | GenAI Platform';
    document.title = title;
  }, [activeTab]);

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        onNavigate={handleTabChange}
        onOpenArchitecture={() => setIsArchitectureOpen(true)}
        systemStatus={systemStatus}
        statusDetail={statusDetail}
      />

      {/* 5-Second Evaluator Value Proposition Hero */}
      <HeroBanner
        onOpenArchitecture={() => setIsArchitectureOpen(true)}
        onSelectTab={handleTabChange}
      />

      {/* Main Tab Navigation Bar */}
      <nav className="tab-bar" role="tablist" aria-label="Main Navigation Tabs">
        <button
          type="button"
          role="tab"
          id="tab-chat"
          aria-selected={activeTab === 'chat'}
          aria-controls="panel-chat"
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => handleTabChange('chat')}
        >
          <span className="tab-icon" aria-hidden="true">💬</span>
          <span>AI Copilot (Pinecone RAG)</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-extract"
          aria-selected={activeTab === 'extract'}
          aria-controls="panel-extract"
          className={`tab-btn ${activeTab === 'extract' ? 'active' : ''}`}
          onClick={() => handleTabChange('extract')}
        >
          <span className="tab-icon" aria-hidden="true">📷</span>
          <span>Multimodal Extraction</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-knowledge"
          aria-selected={activeTab === 'knowledge'}
          aria-controls="panel-knowledge"
          className={`tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => handleTabChange('knowledge')}
        >
          <span className="tab-icon" aria-hidden="true">📚</span>
          <span>Vector Knowledge & DB</span>
        </button>
      </nav>

      {/* Main View Area wrapped in Error Boundary */}
      <main id="main-content" role="main" tabIndex="-1">
        <ErrorBoundary key={activeTab} onReset={() => handleTabChange('chat')}>
          {activeTab === 'chat' && (
            <div id="panel-chat" role="tabpanel" aria-labelledby="tab-chat">
              <ChatTab onNotify={addToast} />
            </div>
          )}
          {activeTab === 'extract' && (
            <div id="panel-extract" role="tabpanel" aria-labelledby="tab-extract">
              <ExtractTab onNotify={addToast} />
            </div>
          )}
          {activeTab === 'knowledge' && (
            <div id="panel-knowledge" role="tabpanel" aria-labelledby="tab-knowledge">
              <KnowledgeTab onNotify={addToast} />
            </div>
          )}
          {activeTab === '404' && (
            <NotFoundPage onNavigate={handleTabChange} />
          )}
        </ErrorBoundary>
      </main>

      {/* Interactive System Architecture & Data Flow Modal */}
      <ArchitectureModal
        isOpen={isArchitectureOpen}
        onClose={() => setIsArchitectureOpen(false)}
        systemStatus={systemStatus}
        statusDetail={statusDetail}
        subsystems={subsystems}
      />

      {/* Global Toast Feedback */}
      <Toast toasts={toasts} onDismiss={dismissToast} />

      {/* Comprehensive Production Footer */}
      <Footer onNavigate={handleTabChange} activeTab={activeTab} />
    </div>
  );
}
