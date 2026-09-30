import React, {
    useState,
    useRef,
    useEffect,
} from 'react';

import { api } from '../services/api';


export default function ChatTab() {

    /* ========================================================
       STATE
    ======================================================== */

    const [messages, setMessages] =
        useState([
            {
                role: 'assistant',

                content:
                    'Welcome to the CODE_STORM AI Copilot. Ask questions regarding our verified guidelines, domain knowledge, or real-time workflows.',

                provider: 'System',

                sources: [],
            },
        ]);


    const [inputQuery, setInputQuery] =
        useState('');


    const [isLoading, setIsLoading] =
        useState(false);


    const messagesEndRef =
        useRef(null);


    /* ========================================================
       SCROLL TO BOTTOM
    ======================================================== */

    const scrollToBottom = () => {

        messagesEndRef.current?.scrollIntoView({
            behavior: 'smooth',
        });

    };


    useEffect(() => {

        scrollToBottom();

    }, [
        messages,
        isLoading,
    ]);


    /* ========================================================
       SEND MESSAGE
    ======================================================== */

    const handleSend = async (e) => {

        e.preventDefault();

        if (
            !inputQuery.trim() ||
            isLoading
        ) {
            return;
        }


        const userText =
            inputQuery.trim();


        setInputQuery('');


        /* Add user message */

        setMessages((prev) => [
            ...prev,

            {
                role: 'user',
                content: userText,
            },
        ]);


        setIsLoading(true);


        try {

            /* =================================================
               CASE 8 API CALL
            ================================================= */

            const data =
                await api.processQuery(
                    userText
                );


            /* =================================================
               ASSISTANT RESPONSE
            ================================================= */

            setMessages((prev) => [
                ...prev,

                {
                    role: 'assistant',

                    content:
                        data.response ||
                        'No response received from the AI service.',

                    provider:
                        data.provider_used ||
                        'Unknown',

                    sources:
                        data.sources || [],
                },
            ]);

        } catch (err) {

            /* =================================================
               ERROR
            ================================================= */

            setMessages((prev) => [
                ...prev,

                {
                    role: 'assistant',

                    content:
                        `⚠️ Error: ${err.message}. Please make sure the FastAPI backend is running on port 8000.`,

                    provider: 'Error',

                    sources: [],
                },
            ]);

        } finally {

            setIsLoading(false);

        }
    };


    /* ========================================================
       UI
    ======================================================== */

    return (

        <div className="glass-card">

            {/* =================================================
                HEADER
            ================================================= */}

            <div className="card-header">

                <h2 className="card-title">
                    💬 AI Domain Copilot
                </h2>

                <p className="card-subtitle">
                    Text → Safety → ChromaDB RAG →
                    Groq/Gemini semantic processing.
                </p>

            </div>


            {/* =================================================
                CHAT WINDOW
            ================================================= */}

            <div className="chat-window">

                <div className="messages-list">

                    {/* =================================================
                        MESSAGES
                    ================================================= */}

                    {messages.map(
                        (message, index) => (

                            <div
                                key={index}
                                className={
                                    `message-bubble ${message.role}`
                                }
                            >

                                <div
                                    style={{
                                        whiteSpace:
                                            'pre-wrap',
                                    }}
                                >
                                    {message.content}
                                </div>


                                {/* =================================================
                                    ASSISTANT META
                                ================================================= */}

                                {message.role ===
                                    'assistant' && (

                                    <div className="bubble-meta">

                                        <span>
                                            ⚡ Served by:{' '}

                                            <strong>
                                                {
                                                    message.provider
                                                }
                                            </strong>
                                        </span>


                                        {/* SOURCES */}

                                        {message.sources &&
                                            message.sources.length >
                                                0 && (

                                            <div
                                                style={{
                                                    display:
                                                        'flex',

                                                    gap:
                                                        '0.4rem',

                                                    flexWrap:
                                                        'wrap',
                                                }}
                                            >

                                                {message.sources.map(
                                                    (
                                                        source,
                                                        sourceIndex
                                                    ) => (

                                                        <span
                                                            key={
                                                                sourceIndex
                                                            }
                                                            className="source-tag"
                                                        >
                                                            📄{' '}
                                                            {
                                                                source
                                                            }
                                                        </span>

                                                    )
                                                )}

                                            </div>

                                        )}

                                    </div>

                                )}

                            </div>

                        )
                    )}


                    {/* =================================================
                        LOADING
                    ================================================= */}

                    {isLoading && (

                        <div
                            className="message-bubble assistant"

                            style={{
                                fontStyle:
                                    'italic',

                                color:
                                    '#94a3b8',
                            }}
                        >
                            ⚡ Consulting verified
                            guidelines & synthesizing
                            response...
                        </div>

                    )}


                    <div
                        ref={messagesEndRef}
                    />

                </div>


                {/* =================================================
                    INPUT
                ================================================= */}

                <form
                    onSubmit={handleSend}
                    className="chat-input-area"
                >

                    <input
                        type="text"

                        className="chat-input"

                        placeholder="Ask a question or enter a task prompt..."

                        value={inputQuery}

                        onChange={(e) =>
                            setInputQuery(
                                e.target.value
                            )
                        }

                        disabled={isLoading}
                    />


                    <button
                        type="submit"

                        className="primary-btn"

                        disabled={
                            isLoading ||
                            !inputQuery.trim()
                        }
                    >
                        {isLoading
                            ? 'Sending...'
                            : 'Send ➜'}
                    </button>

                </form>

            </div>

        </div>
    );
}