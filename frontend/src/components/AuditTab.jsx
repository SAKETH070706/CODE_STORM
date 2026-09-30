import React, {
    useEffect,
    useState,
} from 'react';

import { api } from '../services/api';


export default function AuditTab() {

    const [events, setEvents] = useState([]);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState('');


    /* ========================================================
       LOAD AUDIT EVENTS
    ======================================================== */

    const loadAudit = async () => {

        setLoading(true);
        setError('');

        try {

            const data =
                await api.getAuditEvents();


            /*
             * Support the different response
             * structures that the backend may return.
             */

            const items =
                Array.isArray(data)
                    ? data
                    : data.events ||
                      data.audit ||
                      data.items ||
                      [];


            setEvents(items);

        } catch (err) {

            setError(
                err.message ||
                'Could not load audit events.'
            );

        } finally {

            setLoading(false);

        }
    };


    /* ========================================================
       INITIAL LOAD
    ======================================================== */

    useEffect(() => {

        loadAudit();

    }, []);


    /* ========================================================
       REFRESH
    ======================================================== */

    const handleRefresh = () => {

        loadAudit();

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
                        🧾 Audit Ledger
                    </h2>

                    <p className="card-subtitle">
                        Immutable governance events
                        generated during action processing.
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
                    Loading audit events...
                </div>

            ) : events.length === 0 ? (

                /* ==================================================
                   EMPTY STATE
                ================================================== */

                <div className="empty-state">
                    No audit events available.
                </div>

            ) : (

                /* ==================================================
                   AUDIT EVENTS
                ================================================== */

                <div className="audit-list">

                    {events.map(
                        (event, index) => {

                            const eventId =
                                event.id ||
                                event.event_id ||
                                index;


                            const eventType =
                                event.event_type ||
                                event.type ||
                                'EVENT';


                            const timestamp =
                                event.created_at ||
                                event.timestamp ||
                                '—';


                            const actionId =
                                event.action_id ||
                                '—';


                            const details =
                                event.details ||
                                {};


                            return (
                                <div
                                    className="audit-event"
                                    key={eventId}
                                >

                                    {/* ==================================
                                        TIMELINE DOT
                                    ================================== */}

                                    <div className="audit-dot" />


                                    {/* ==================================
                                        EVENT CONTENT
                                    ================================== */}

                                    <div className="audit-content">

                                        {/* EVENT HEADER */}

                                        <div className="audit-top">

                                            <strong>
                                                {eventType}
                                            </strong>

                                            <span>
                                                {timestamp}
                                            </span>

                                        </div>


                                        {/* ACTION */}

                                        <div className="audit-action">

                                            Action:{' '}

                                            <span className="mono">
                                                {actionId}
                                            </span>

                                        </div>


                                        {/* DETAILS */}

                                        <pre className="audit-details">
                                            {JSON.stringify(
                                                details,
                                                null,
                                                2
                                            )}
                                        </pre>

                                    </div>

                                </div>
                            );

                        }
                    )}

                </div>

            )}

        </div>
    );
}