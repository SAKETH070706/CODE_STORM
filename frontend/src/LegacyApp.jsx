import React, { useState } from 'react';
import Navbar from './components/Navbar';
import ChatTab from './components/ChatTab';
import ExtractTab from './components/ExtractTab';
import KnowledgeTab from './components/KnowledgeTab';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="app-container">
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

      <main>
        {activeTab === 'chat' && <ChatTab />}
        {activeTab === 'extract' && <ExtractTab />}
        {activeTab === 'knowledge' && <KnowledgeTab />}
      </main>
    </div>
  );
}
