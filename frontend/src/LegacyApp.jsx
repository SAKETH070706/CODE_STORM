import React, { useState } from 'react';
import {ErrorBoundary} from './workspace/shared';
import Navbar from './components/Navbar';
import ChatTab from './components/ChatTab';
import ExtractTab from './components/ExtractTab';
import KnowledgeTab from './components/KnowledgeTab';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="app-container">
      <div style={{background: '#0f172a', padding: '8px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #334155'}}>
        <span style={{color: '#94a3b8', fontSize: '13px', fontWeight: '500'}}>AI Copilot Mode (Pinecone RAG + Multimodal)</span>
        <button onClick={() => window.location.href = '/'} style={{background: '#2563eb', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: '600'}}>
          &larr; Switch to PNG5 Governor Workspace
        </button>
      </div>
      <Navbar />

      <nav className="tab-bar">
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 AI Copilot (RAG)
        </button>
        <button
          className={`tab-btn ${activeTab === 'extract' ? 'active' : ''}`}
          onClick={() => setActiveTab('extract')}
        >
          📷 Multimodal Extraction
        </button>
        <button
          className={`tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => setActiveTab('knowledge')}
        >
          📚 Vector Knowledge
        </button>
      </nav>

      <main><ErrorBoundary key={activeTab}>
        {activeTab === 'chat' && <ChatTab />}
        {activeTab === 'extract' && <ExtractTab />}
        {activeTab === 'knowledge' && <KnowledgeTab />}
      </ErrorBoundary></main>
    </div>
  );
}
