import React, {
    useEffect,
    useState,
} from 'react';

import { api } from '../services/api';


export default function ApprovalsTab() {

    /* ========================================================
       STATE
    ======================================================== */

    const [approvals, setApprovals] =
        useState([]);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState('');

    const [processingId, setProcessingId] =
        useState(null);


    /* ========================================================
       LOAD APPROVALS
    ======================================================== */

    const loadApprovals = async () => {

        setLoading(true);
        setError('');

        try {

            const data =
                await api.getApprovals();


            /*
             * Backend may return:
             *
             * [
             *   ...
             * ]
             *
             * or:
             *
             * {
             *   approvals: [...]
             * }
             *
             * or:
             *
             * {
             *   items: [...]
             * }
             */

            const items =
                Array.isArray(data)
                    ? data
                    : data.approvals ||
                      data.items ||
                      [];


            setApprovals(items);

        } catch (err) {

            setError(
                err.message ||
                'Could not load approvals.'
            );

        } finally {

            setLoading(false);

        }
    };


    /* ========================================================
       INITIAL LOAD
    ======================================================== */

    useEffect(() => {

        loadApprovals();

    }, []);


    /* ========================================================
       APPROVE
    ======================================================== */

    const handleApprove = async (
        approvalId
    ) => {

        if (!approvalId) {
            return;
        }

        setProcessingId(
            approvalId
        );

        setError('');

        try {

            await api.approveAction(
                approvalId,
                'Approved by dashboard reviewer'
            );


            /*
             * Reload the approval queue
             * after the decision.
             */

            await loadApprovals();

        } catch (err) {

            setError(
                err.message ||
                'Could not approve action.'
            );

        } finally {

            setProcessingId(null);

        }
    };


    /* ========================================================
       REJECT
    ======================================================== */

    const handleReject = async (
        approvalId
    ) => {

        if (!approvalId) {
            return;
        }

        setProcessingId(
            approvalId
        );

        setError('');

        try {

            await api.rejectAction(
                approvalId,
                'Rejected by dashboard reviewer'
            );


            /*
             * Reload the approval queue
             * after the decision.
             */

            await loadApprovals();

        } catch (err) {

            setError(
                err.message ||
                'Could not reject action.'
            );

        } finally {

            setProcessingId(null);

        }
    };


    /* ========================================================
       REFRESH
    ======================================================== */

    const handleRefresh = () => {

        loadApprovals();

    };


    /* ========================================================
       RENDER
    ======================================================== */

    return (

        <div className="glass-card">

            {/* =================================================
                HEADER
            ================================================= */}

            <div className="card-header action-header">

                <div>

                    <h2 className="card-title">
                        🛡️ Human Approvals
                    </h2>

                    <p className="card-subtitle">
                        Review high-risk or externally
                        directed actions before execution.
                    </p>

                </div>


                <button
                    type="button"
                    className="secondary-btn"
                    onClick={handleRefresh}
                    disabled={loading}
                >

                    {loading
                        ? '⏳ Loading...'
                        : '🔄 Refresh'}

                </button>

            </div>


            {/* =================================================
                ERROR
            ================================================= */}

            {error && (

                <div className="error-box">
                    ⚠️ {error}
                </div>

            )}


            {/* =================================================
                LOADING
            ================================================= */}

            {loading ? (

                <div className="empty-state">
                    Loading approval queue...
                </div>

            ) : approvals.length === 0 ? (

                /* =================================================
                   EMPTY STATE
                ================================================= */

                <div className="empty-state">

                    No pending approvals.

                </div>

            ) : (

                /* =================================================
                   APPROVAL LIST
                ================================================= */

                <div className="approval-list">

                    {approvals.map(
                        (approval) => {

                            const state =
                                String(
                                    approval.state ||
                                    ''
                                ).toUpperCase();


                            const approvalId =
                                approval.approval_id ||
                                approval.id;


                            const pending =
                                state === 'PENDING';


                            const isProcessing =
                                processingId ===
                                approvalId;


                            return (

                                <div
                                    className="approval-card"
                                    key={approvalId}
                                >

                                    {/* =================================
                                        CARD HEADER
                                    ================================= */}

                                    <div className="approval-card-header">

                                        <div>

                                            <div className="decision-label">
                                                APPROVAL REQUEST
                                            </div>

                                            <h3>
                                                {approval.tool ||
                                                    approval.action?.tool ||
                                                    'Governed Action'}
                                            </h3>

                                        </div>


                                        <span
                                            className={
                                                `status-pill ${
                                                    state.toLowerCase()
                                                }`
                                            }
                                        >
                                            {state || 'UNKNOWN'}
                                        </span>

                                    </div>


                                    {/* =================================
                                        APPROVAL INFORMATION
                                    ================================= */}

                                    <div className="approval-info">

                                        {/* Approval ID */}

                                        <div>

                                            <span>
                                                Approval ID
                                            </span>

                                            <strong className="mono">
                                                {approvalId ||
                                                    '—'}
                                            </strong>

                                        </div>


                                        {/* Action ID */}

                                        <div>

                                            <span>
                                                Action ID
                                            </span>

                                            <strong className="mono">

                                                {approval.action_id ||
                                                    approval.action?.action_id ||
                                                    '—'}

                                            </strong>

                                        </div>


                                        {/* Requested By */}

                                        <div>

                                            <span>
                                                Requested By
                                            </span>

                                            <strong>
                                                {approval.requested_by ||
                                                    '—'}
                                            </strong>

                                        </div>

                                    </div>


                                    {/* =================================
                                        OPTIONAL DETAILS
                                    ================================= */}

                                    {(approval.reason ||
                                        approval.decision_reason ||
                                        approval.expires_at) && (

                                        <div className="approval-info">

                                            {(approval.reason ||
                                                approval.decision_reason) && (

                                                <div>

                                                    <span>
                                                        Reason
                                                    </span>

                                                    <strong>
                                                        {approval.reason ||
                                                            approval.decision_reason}
                                                    </strong>

                                                </div>

                                            )}


                                            {approval.expires_at && (

                                                <div>

                                                    <span>
                                                        Expires
                                                    </span>

                                                    <strong>
                                                        {approval.expires_at}
                                                    </strong>

                                                </div>

                                            )}

                                        </div>

                                    )}


                                    {/* =================================
                                        ACTION BUTTONS
                                    ================================= */}

                                    {pending && (

                                        <div className="approval-actions">

                                            {/* APPROVE */}

                                            <button
                                                type="button"
                                                className="approve-btn"
                                                disabled={
                                                    isProcessing
                                                }
                                                onClick={() =>
                                                    handleApprove(
                                                        approvalId
                                                    )
                                                }
                                            >

                                                {isProcessing
                                                    ? 'Processing...'
                                                    : '✓ Approve'}

                                            </button>


                                            {/* REJECT */}

                                            <button
                                                type="button"
                                                className="reject-btn"
                                                disabled={
                                                    isProcessing
                                                }
                                                onClick={() =>
                                                    handleReject(
                                                        approvalId
                                                    )
                                                }
                                            >

                                                {isProcessing
                                                    ? 'Processing...'
                                                    : '✕ Reject'}

                                            </button>

                                        </div>

                                    )}

                                </div>

                            );

                        }
                    )}

                </div>

            )}

        </div>
    );
}