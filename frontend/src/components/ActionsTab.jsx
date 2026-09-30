import React, {
    useEffect,
    useState,
} from 'react';

import { api } from '../services/api';

import DecisionCard from './DecisionCard';


export default function ActionsTab() {

    /* ========================================================
       STATE
    ======================================================== */

    const [actions, setActions] =
        useState([]);

    const [selectedAction, setSelectedAction] =
        useState(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState('');


    /* ========================================================
       LOAD ACTIONS
    ======================================================== */

    const loadActions = async () => {

        setLoading(true);
        setError('');

        try {

            const data =
                await api.getActions();


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
             *   actions: [...]
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
                    : data.actions ||
                      data.items ||
                      [];


            setActions(items);

        } catch (err) {

            setError(
                err.message ||
                'Could not load actions.'
            );

        } finally {

            setLoading(false);

        }
    };


    /* ========================================================
       INITIAL LOAD
    ======================================================== */

    useEffect(() => {

        loadActions();

    }, []);


    /* ========================================================
       SELECT ACTION
    ======================================================== */

    const handleSelect = async (id) => {

        if (!id) {
            return;
        }

        try {

            setError('');

            const data =
                await api.getAction(id);

            setSelectedAction(data);

        } catch (err) {

            setError(
                err.message ||
                'Could not load action details.'
            );

        }
    };


    /* ========================================================
       REFRESH
    ======================================================== */

    const handleRefresh = () => {

        setSelectedAction(null);

        loadActions();

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
                        ⚡ Live Activity
                    </h2>

                    <p className="card-subtitle">
                        Governed agent actions and
                        execution decisions.
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
                    Loading actions...
                </div>

            ) : actions.length === 0 ? (

                /* =================================================
                   EMPTY
                ================================================= */

                <div className="empty-state">

                    No governed actions yet.

                    <br />

                    Run an agent workflow
                    to create one.

                </div>

            ) : (

                /* =================================================
                   ACTION TABLE
                ================================================= */

                <div className="table-wrapper">

                    <table className="data-table">

                        <thead>

                            <tr>

                                <th>
                                    Action
                                </th>

                                <th>
                                    Tool
                                </th>

                                <th>
                                    Resource
                                </th>

                                <th>
                                    Decision
                                </th>

                                <th>
                                    State
                                </th>

                                <th>
                                    Risk
                                </th>

                            </tr>

                        </thead>


                        <tbody>

                            {actions.map(
                                (action) => {

                                    const actionId =
                                        action.action_id ||
                                        action.id ||
                                        '';

                                    const decision =
                                        action.decision ||
                                        '';

                                    const risk =
                                        action.risk_score ??
                                        action.risk?.score ??
                                        '—';


                                    return (

                                        <tr
                                            key={actionId}
                                            onClick={() =>
                                                handleSelect(
                                                    actionId
                                                )
                                            }
                                            className="clickable-row"
                                        >

                                            {/* ACTION ID */}

                                            <td className="mono">

                                                {actionId
                                                    ? actionId.slice(
                                                        0,
                                                        12
                                                    )
                                                    : '—'}

                                            </td>


                                            {/* TOOL */}

                                            <td>
                                                {action.tool ||
                                                    '—'}
                                            </td>


                                            {/* RESOURCE */}

                                            <td>
                                                {action.resource ||
                                                    '—'}
                                            </td>


                                            {/* DECISION */}

                                            <td>

                                                <span
                                                    className={
                                                        `status-pill ${
                                                            String(
                                                                decision
                                                            ).toLowerCase()
                                                        }`
                                                    }
                                                >
                                                    {decision ||
                                                        '—'}
                                                </span>

                                            </td>


                                            {/* STATE */}

                                            <td>
                                                {action.state ||
                                                    '—'}
                                            </td>


                                            {/* RISK */}

                                            <td>
                                                {risk}
                                            </td>

                                        </tr>

                                    );

                                }
                            )}

                        </tbody>

                    </table>

                </div>

            )}


            {/* =================================================
                ACTION DETAILS
            ================================================= */}

            {selectedAction && (

                <div className="detail-panel">

                    <div className="section-title">
                        Action Details
                    </div>


                    <DecisionCard
                        result={
                            selectedAction
                        }
                    />


                    <pre className="json-display">
                        {JSON.stringify(
                            selectedAction,
                            null,
                            2
                        )}
                    </pre>

                </div>

            )}

        </div>
    );
}