import React, { useState } from 'react';
import { api } from '../services/api';
import DecisionCard from './DecisionCard';

export default function AgentTab() {
    const [taskId, setTaskId] = useState('sales-report');

    const [instruction, setInstruction] = useState(
        'Read the monthly sales summary'
    );

    const [tool, setTool] = useState(
        'database.read'
    );

    const [resource, setResource] = useState(
        'sales_summary'
    );

    const [argumentsText, setArgumentsText] = useState(
        JSON.stringify(
            {
                action: 'read',
                columns: [
                    'month',
                    'total_sales',
                ],
            },
            null,
            2
        )
    );

    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);


    /* ============================================================
       RUN GOVERNED AGENT
    ============================================================ */

    const handleRun = async (event) => {
        event.preventDefault();

        if (loading) {
            return;
        }

        setError('');
        setResult(null);

        let argumentsObject;

        try {
            argumentsObject = JSON.parse(
                argumentsText
            );
        } catch {
            setError(
                'Arguments must contain valid JSON.'
            );
            return;
        }

        setLoading(true);

        try {
            const response = await api.runAgent({
                task_id: taskId,
                instruction: instruction,
                tool: tool,
                resource: resource,
                arguments: argumentsObject,
            });

            setResult(response);

        } catch (err) {
            setError(
                err.message ||
                'Agent workflow failed.'
            );

        } finally {
            setLoading(false);
        }
    };


    /* ============================================================
       SAFE READ EXAMPLE
    ============================================================ */

    const loadReadExample = () => {
        setTaskId('sales-report');

        setInstruction(
            'Read the monthly sales summary'
        );

        setTool('database.read');

        setResource('sales_summary');

        setArgumentsText(
            JSON.stringify(
                {
                    action: 'read',
                    columns: [
                        'month',
                        'total_sales',
                    ],
                },
                null,
                2
            )
        );

        setError('');
        setResult(null);
    };


    /* ============================================================
       DELETE TEST EXAMPLE
    ============================================================ */

    const loadDeleteExample = () => {
        setTaskId('sales-report');

        setInstruction(
            'Delete the sales database'
        );

        setTool('database.read');

        setResource('sales_summary');

        setArgumentsText(
            JSON.stringify(
                {
                    action: 'delete',
                },
                null,
                2
            )
        );

        setError('');
        setResult(null);
    };


    /* ============================================================
       APPROVAL TEST EXAMPLE
    ============================================================ */

    const loadSendExample = () => {
        setTaskId('sales-report');

        setInstruction(
            'Send the monthly sales report to the approved external destination'
        );

        setTool('send.report');

        setResource(
            'approved_external_destination'
        );

        setArgumentsText(
            JSON.stringify(
                {
                    action: 'send',
                    destination:
                        'approved_external_destination',
                    report_path:
                        'monthly_sales_report.json',
                },
                null,
                2
            )
        );

        setError('');
        setResult(null);
    };


    /* ============================================================
       RENDER
    ============================================================ */

    return (
        <div className="glass-card">

            {/* ======================================================
               HEADER
            ====================================================== */}

            <div className="card-header">

                <h2 className="card-title">
                    🤖 Agent Permission Governor
                </h2>

                <p className="card-subtitle">
                    Case 7/8 agent workflow:
                    instruction → semantic planning →
                    safety → RAG → Governor → execution.
                </p>

            </div>


            {/* ======================================================
               EXAMPLE BUTTONS
            ====================================================== */}

            <div className="example-buttons">

                <button
                    type="button"
                    className="secondary-btn"
                    onClick={loadReadExample}
                    disabled={loading}
                >
                    ✓ Safe Read
                </button>


                <button
                    type="button"
                    className="secondary-btn danger-outline"
                    onClick={loadDeleteExample}
                    disabled={loading}
                >
                    ⛔ Delete Test
                </button>


                <button
                    type="button"
                    className="secondary-btn warning-outline"
                    onClick={loadSendExample}
                    disabled={loading}
                >
                    🛡️ Approval Test
                </button>

            </div>


            {/* ======================================================
               FORM
            ====================================================== */}

            <form
                className="agent-form"
                onSubmit={handleRun}
            >

                {/* ==================================================
                   TASK ID + TOOL
                ================================================== */}

                <div className="form-row">

                    <div className="form-group">

                        <label>
                            Task ID
                        </label>

                        <input
                            className="form-input"
                            value={taskId}
                            onChange={(e) =>
                                setTaskId(
                                    e.target.value
                                )
                            }
                            disabled={loading}
                        />

                    </div>


                    <div className="form-group">

                        <label>
                            Tool
                        </label>

                        <input
                            className="form-input"
                            value={tool}
                            onChange={(e) =>
                                setTool(
                                    e.target.value
                                )
                            }
                            disabled={loading}
                        />

                    </div>

                </div>


                {/* ==================================================
                   RESOURCE
                ================================================== */}

                <div className="form-group">

                    <label>
                        Resource
                    </label>

                    <input
                        className="form-input"
                        value={resource}
                        onChange={(e) =>
                            setResource(
                                e.target.value
                            )
                        }
                        disabled={loading}
                    />

                </div>


                {/* ==================================================
                   AGENT INSTRUCTION
                ================================================== */}

                <div className="form-group">

                    <label>
                        Agent Instruction
                    </label>

                    <textarea
                        className="form-textarea"
                        rows="4"
                        value={instruction}
                        onChange={(e) =>
                            setInstruction(
                                e.target.value
                            )
                        }
                        disabled={loading}
                    />

                </div>


                {/* ==================================================
                   ACTION ARGUMENTS
                ================================================== */}

                <div className="form-group">

                    <label>
                        Action Arguments
                    </label>

                    <textarea
                        className="form-textarea mono-input"
                        rows="8"
                        value={argumentsText}
                        onChange={(e) =>
                            setArgumentsText(
                                e.target.value
                            )
                        }
                        disabled={loading}
                    />

                </div>


                {/* ==================================================
                   SUBMIT
                ================================================== */}

                <button
                    className="primary-btn"
                    type="submit"
                    disabled={
                        loading ||
                        !instruction.trim()
                    }
                >
                    {loading
                        ? '⏳ Running Governor...'
                        : '🚀 Run Governed Agent'}
                </button>

            </form>


            {/* ======================================================
               ERROR
            ====================================================== */}

            {error && (
                <div className="error-box">
                    ⚠️ {error}
                </div>
            )}


            {/* ======================================================
               RESULT
            ====================================================== */}

            {result && (
                <div className="result-section">

                    <DecisionCard
                        result={result}
                    />


                    {/* ==================================================
                       EXECUTION RESULT
                    ================================================== */}

                    {result.execution && (
                        <div className="execution-result">

                            <div className="section-title">
                                ⚙️ Execution Result
                            </div>

                            <pre className="json-display">
                                {JSON.stringify(
                                    result.execution,
                                    null,
                                    2
                                )}
                            </pre>

                        </div>
                    )}

                </div>
            )}

        </div>
    );
}