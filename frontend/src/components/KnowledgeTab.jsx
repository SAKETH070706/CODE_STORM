import React, {
    useEffect,
    useState
} from 'react';

import { api } from '../services/api';

export default function KnowledgeTab() {

    const [chunks, setChunks] =
        useState(0);

    const [loading, setLoading] =
        useState(false);

    const [message, setMessage] =
        useState('');

    const [error, setError] =
        useState('');


    /* ========================================================
       LOAD RAG STATISTICS
    ======================================================== */

    const loadStats = async () => {

        try {

            setError('');

            const data =
                await api.ragStats();

            setChunks(
                data.total_chunks || 0
            );

        } catch (err) {

            setChunks(0);

            setError(
                err.message ||
                'Unable to load knowledge base statistics.'
            );
        }
    };


    /* ========================================================
       INITIAL LOAD
    ======================================================== */

    useEffect(() => {

        loadStats();

    }, []);


    /* ========================================================
       INGEST KNOWLEDGE
    ======================================================== */

    const ingest = async () => {

        if (loading) {
            return;
        }

        setLoading(true);
        setMessage('');
        setError('');

        try {

            const data =
                await api.ragIngest();

            setMessage(
                `Indexed ${
                    data.chunks_ingested || 0
                } chunks successfully.`
            );

            await loadStats();

        } catch (err) {

            setError(
                err.message ||
                'Knowledge base indexing failed.'
            );

        } finally {

            setLoading(false);
        }
    };


    /* ========================================================
       RENDER
    ======================================================== */

    return (

        <div className="stack">

            {/* =================================================
                PAGE HEADER
            ================================================= */}

            <div className="page-title">

                <div>

                    <div className="eyebrow">
                        SEMANTIC ASSISTANCE
                    </div>

                    <h1>
                        Policy Knowledge
                    </h1>

                    <p>
                        Local policy and knowledge
                        retrieval used as optional
                        semantic assistance.
                    </p>

                </div>

            </div>


            {/* =================================================
                METRICS
            ================================================= */}

            <div className="metrics">

                <div className="metric">

                    <strong>
                        {chunks}
                    </strong>

                    <span>
                        Vector Chunks
                    </span>

                </div>


                <div className="metric">

                    <strong>
                        0.70
                    </strong>

                    <span>
                        Max Cosine Distance
                    </span>

                </div>


                <div className="metric">

                    <strong>
                        LOCAL
                    </strong>

                    <span>
                        Processing Mode
                    </span>

                </div>

            </div>


            {/* =================================================
                KNOWLEDGE BASE CARD
            ================================================= */}

            <section className="card">

                <div className="eyebrow">
                    LOCAL VECTOR STORE
                </div>


                <h2>
                    Knowledge Base
                </h2>


                <code>
                    backend/data/knowledge/
                </code>


                <p>
                    Policy and risk knowledge can
                    be indexed into ChromaDB and
                    retrieved by the semantic
                    assistance layer.
                </p>


                <button
                    className="primary"
                    onClick={ingest}
                    disabled={loading}
                >

                    {loading
                        ? 'Indexing…'
                        : '↻ Re-index Knowledge Base'}

                </button>


                {/* SUCCESS */}

                {message && (

                    <div
                        className="notice"
                        style={{
                            marginTop: '1rem'
                        }}
                    >
                        ✅ {message}
                    </div>

                )}


                {/* ERROR */}

                {error && (

                    <div
                        className="notice"
                        style={{
                            marginTop: '1rem',
                            border:
                                '1px solid rgba(239,68,68,0.45)',
                            background:
                                'rgba(239,68,68,0.10)',
                            color: '#fecaca'
                        }}
                    >
                        ⚠️ {error}
                    </div>

                )}

            </section>


            {/* =================================================
                CASE 8 SECURITY INFORMATION
            ================================================= */}

            <section className="card">

                <div className="eyebrow">
                    SECURITY RULE
                </div>


                <h2>
                    Semantic assistance is not authorization
                </h2>


                <p>
                    Retrieved policy text and LLM
                    classifications can assist
                    ambiguous decisions, but explicit
                    authorization and hard-denial
                    rules remain authoritative.
                </p>


                {/* CASE 8 FLOW */}

                <div
                    style={{
                        marginTop: '1rem',
                        padding: '0.9rem 1rem',
                        borderRadius: '10px',
                        background:
                            'rgba(59,130,246,0.08)',
                        border:
                            '1px solid rgba(59,130,246,0.2)',
                        color: '#cbd5e1',
                        fontSize: '0.9rem'
                    }}
                >

                    <strong>
                        Case 8 semantic flow
                    </strong>


                    <div
                        style={{
                            marginTop: '0.5rem',
                            lineHeight: 1.7
                        }}
                    >
                        Instruction
                        {' → '}
                        Safety Scan
                        {' → '}
                        ChromaDB Retrieval
                        {' → '}
                        LLM Analysis
                        {' → '}
                        Governor
                    </div>

                </div>


                {/* SECURITY GUARANTEE */}

                <div
                    style={{
                        marginTop: '1rem',
                        padding: '0.9rem 1rem',
                        borderRadius: '10px',
                        background:
                            'rgba(16,185,129,0.08)',
                        border:
                            '1px solid rgba(16,185,129,0.20)',
                        color: '#d1fae5',
                        fontSize: '0.9rem'
                    }}
                >

                    🔐 The semantic layer can propose
                    an action, but it cannot authorize
                    or execute that action.

                </div>

            </section>

        </div>

    );
}