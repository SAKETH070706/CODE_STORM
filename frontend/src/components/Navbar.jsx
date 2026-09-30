import React, { useEffect, useState } from 'react';
import { checkReadiness, checkHealth } from '../api/health';

export default function Navbar() {
  const [systemStatus, setSystemStatus] = useState('CHECKING'); // ONLINE | DEGRADED | OFFLINE | CHECKING
  const [statusDetail, setStatusDetail] = useState('Connecting to backend...');
  const [providerInfo, setProviderInfo] = useState({
    db: 'PostgreSQL',
    vector: 'Pinecone',
    primaryLlm: 'Groq',
    fallbackLlm: 'Gemini'
  });

  useEffect(() => {
    let isMounted = true;

    const pollHealth = async () => {
      try {
        const readyData = await checkReadiness();
        if (!isMounted) return;

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
      } catch (err) {
        if (!isMounted) return;
        // Fallback check to basic health
        try {
          await checkHealth();
          setSystemStatus('DEGRADED');
          setStatusDetail('API Alive (Dependencies Starting)');
        } catch {
          setSystemStatus('OFFLINE');
          setStatusDetail('Backend Disconnected');
        }
      }
    };

    pollHealth();
    const interval = setInterval(pollHealth, 6000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const getStatusColorClass = () => {
    if (systemStatus === 'ONLINE') return 'online';
    if (systemStatus === 'DEGRADED') return 'degraded';
    if (systemStatus === 'OFFLINE') return 'offline';
    return 'checking';
  };

  return (
    <header className="navbar">
      <div className="brand">
        <div className="brand-icon">⚡</div>
        <div>
          <div className="brand-logo">CODE_STORM</div>
          <div className="brand-tag">Production GenAI Platform</div>
        </div>
      </div>

      <div className="nav-badges">
        <div className="model-pill" title="Primary High-Speed LLM Inference">
          Groq: <span>llama-3.3-70b</span>
        </div>
        <div className="model-pill" title="Resilient Fallback LLM Inference">
          Gemini: <span>2.5-flash</span>
        </div>
        <div className="model-pill" title="Vector Database">
          Vector: <span>Pinecone</span>
        </div>

        <div className="status-badge" title={statusDetail}>
          <span className={`status-dot ${getStatusColorClass()}`}></span>
          <span className="status-text">{systemStatus}</span>
        </div>
      </div>
    </header>
  );
}
