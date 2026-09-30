import React, {
    useEffect,
    useState,
} from 'react';

import { api } from '../services/api';


export default function PoliciesTab() {

    /* ========================================================
       STATE
    ======================================================== */

    const [policies, setPolicies] =
        useState([]);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState('');


    /* ========================================================
       LOAD POLICIES
    ======================================================== */

    const loadPolicies = async () => {

        setLoading(true);
        setError('');

        try {

            const data =
                await api.getPolicies();


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
             *   policies: [...]
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
                    : data.policies ||
                      data.items ||
                      [];


            setPolicies(items);

        } catch (err) {

            setError(
                err.message ||
                'Could not load policies.'
            );

        } finally {

            setLoading(false);

        }
    };


    /* ========================================================
       INITIAL LOAD
    ======================================================== */

    useEffect(() => {

        loadPolicies();

    }, []);


    /* ========================================================
       REFRESH
    ======================================================== */

    const handleRefresh = () => {

        loadPolicies();

    };


    /* ========================================================
       RENDER
    ======================================================== */

    return (

        <div className="glass-card">

            {/* ==================================================
                HEADER
            ================================================== */}

            <div className="card-header action-header">

                <div>

                    <h2 className="card-title">
                        📜 Governance Policies
                    </h2>

                    <p className="card-subtitle">
                        Runtime policy configuration used by
                        the Agent Permission Governor.
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


            {/* ==================================================
                ERROR
            ================================================== */}

            {error && (

                <div className="error-box">
                    ⚠️ {error}
                </div>

            )}


            {/* ==================================================
                LOADING
            ================================================== */}

            {loading ? (

                <div className="empty-state">
                    Loading policies...
                </div>

            ) : policies.length === 0 ? (

                /* ==================================================
                   DEFAULT POLICY CARDS
                ================================================== */

                <div className="policy-grid">

                    {/* DATABASE READ */}

                    <div className="policy-card">

                        <div className="policy-icon">
                            ✓
                        </div>

                        <h3>
                            database.read
                        </h3>

                        <p>
                            Read approved sales resources.
                        </p>

                        <span className="status-pill allow">
                            ALLOW
                        </span>

                    </div>


                    {/* REPORT WRITE */}

                    <div className="policy-card">

                        <div className="policy-icon">
                            📄
                        </div>

                        <h3>
                            report.write
                        </h3>

                        <p>
                            Create reports in the designated
                            reports directory.
                        </p>

                        <span className="status-pill allow">
                            ALLOW
                        </span>

                    </div>


                    {/* SEND REPORT */}

                    <div className="policy-card">

                        <div className="policy-icon">
                            🛡️
                        </div>

                        <h3>
                            send.report
                        </h3>

                        <p>
                            External report sharing requires
                            human approval.
                        </p>

                        <span className="status-pill escalate">
                            ESCALATE
                        </span>

                    </div>


                    {/* DATABASE DELETE */}

                    <div className="policy-card">

                        <div className="policy-icon">
                            ⛔
                        </div>

                        <h3>
                            database.delete
                        </h3>

                        <p>
                            Destructive database operations
                            are not permitted.
                        </p>

                        <span className="status-pill block">
                            BLOCK
                        </span>

                    </div>

                </div>

            ) : (

                /* ==================================================
                   BACKEND POLICIES
                ================================================== */

                <div className="policy-grid">

                    {policies.map(
                        (policy, index) => {

                            const policyId =
                                policy.id ||
                                policy.name ||
                                index;


                            const policyName =
                                policy.name ||
                                policy.tool ||
                                `Policy ${index + 1}`;


                            const description =
                                policy.description ||
                                policy.reason ||
                                'Governance policy';


                            const decision =
                                policy.decision ||
                                '';


                            return (

                                <div
                                    className="policy-card"
                                    key={policyId}
                                >

                                    <div className="policy-icon">
                                        📜
                                    </div>


                                    <h3>
                                        {policyName}
                                    </h3>


                                    <p>
                                        {description}
                                    </p>


                                    {decision && (

                                        <span
                                            className={
                                                `status-pill ${
                                                    String(
                                                        decision
                                                    ).toLowerCase()
                                                }`
                                            }
                                        >
                                            {decision}
                                        </span>

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