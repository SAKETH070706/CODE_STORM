import React from 'react';

export default function DecisionCard({ result }) {
    if (!result) {
        return null;
    }

    const decision = String(
        result.decision || 'UNKNOWN'
    ).toUpperCase();

    const state = String(
        result.state || ''
    ).toUpperCase();

    const decisionClass =
        decision === 'ALLOW'
            ? 'decision-allow'
            : decision === 'BLOCK'
                ? 'decision-block'
                : decision === 'ESCALATE'
                    ? 'decision-escalate'
                    : 'decision-unknown';

    return (
        <div className="decision-card">
            <div className="decision-header">
                <div>
                    <div className="decision-label">
                        GOVERNOR DECISION
                    </div>

                    <div
                        className={`decision-badge ${decisionClass}`}
                    >
                        {decision}
                    </div>
                </div>

                {result.latency_ms !== undefined && (
                    <div className="latency-badge">
                        {Number(result.latency_ms).toFixed(2)} ms
                    </div>
                )}
            </div>

            <div className="decision-grid">

                <div className="decision-field">
                    <span>State</span>
                    <strong>{state || '—'}</strong>
                </div>

                <div className="decision-field">
                    <span>Action ID</span>
                    <strong className="mono">
                        {result.action_id || '—'}
                    </strong>
                </div>

                <div className="decision-field">
                    <span>Risk Score</span>
                    <strong>
                        {result.risk?.score ?? '—'}
                    </strong>
                </div>

                <div className="decision-field">
                    <span>Risk Level</span>
                    <strong>
                        {result.risk?.level || '—'}
                    </strong>
                </div>

            </div>

            {result.reason && (
                <div className="decision-reason">
                    <span>Reason</span>
                    <p>{result.reason}</p>
                </div>
            )}

            {result.risk?.factors?.length > 0 && (
                <div className="risk-factors">
                    <span>Risk Factors</span>

                    <div className="tag-list">
                        {result.risk.factors.map(
                            (factor, index) => (
                                <span
                                    className="risk-tag"
                                    key={index}
                                >
                                    {factor}
                                </span>
                            )
                        )}
                    </div>
                </div>
            )}

            {result.requires_approval && (
                <div className="approval-notice">
                    🛡️ Human approval required before execution.
                </div>
            )}

            {result.approval_id && (
                <div className="decision-field">
                    <span>Approval ID</span>

                    <strong className="mono">
                        {result.approval_id}
                    </strong>
                </div>
            )}
        </div>
    );
}