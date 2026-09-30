import React, { useState } from 'react';

import Navbar from './components/Navbar';

import ChatTab from './components/ChatTab';
import ExtractTab from './components/ExtractTab';
import KnowledgeTab from './components/KnowledgeTab';

import AgentTab from './components/AgentTab';
import ActionsTab from './components/ActionsTab';
import ApprovalsTab from './components/ApprovalsTab';
import AuditTab from './components/AuditTab';
import PoliciesTab from './components/PoliciesTab';

import './App.css';

export default function App() {

    const [activeTab, setActiveTab] =
        useState('agent');

    return (
        <div className="app-container">

            <Navbar />

            <nav className="tab-bar">

                <button
                    className={`tab-btn ${
                        activeTab === 'agent'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('agent')
                    }
                >
                    🤖 Agent Governor
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'actions'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('actions')
                    }
                >
                    ⚡ Live Activity
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'approvals'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('approvals')
                    }
                >
                    🛡️ Approvals
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'audit'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('audit')
                    }
                >
                    🧾 Audit
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'policies'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('policies')
                    }
                >
                    📜 Policies
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'chat'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('chat')
                    }
                >
                    💬 AI Copilot
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'extract'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('extract')
                    }
                >
                    📷 Extraction
                </button>

                <button
                    className={`tab-btn ${
                        activeTab === 'knowledge'
                            ? 'active'
                            : ''
                    }`}
                    onClick={() =>
                        setActiveTab('knowledge')
                    }
                >
                    📚 Knowledge
                </button>

            </nav>

            <main>

                {activeTab === 'agent' && (
                    <AgentTab />
                )}

                {activeTab === 'actions' && (
                    <ActionsTab />
                )}

                {activeTab === 'approvals' && (
                    <ApprovalsTab />
                )}

                {activeTab === 'audit' && (
                    <AuditTab />
                )}

                {activeTab === 'policies' && (
                    <PoliciesTab />
                )}

                {activeTab === 'chat' && (
                    <ChatTab />
                )}

                {activeTab === 'extract' && (
                    <ExtractTab />
                )}

                {activeTab === 'knowledge' && (
                    <KnowledgeTab />
                )}

            </main>

        </div>
    );
}