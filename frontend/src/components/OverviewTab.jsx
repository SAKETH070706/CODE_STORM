import StatusBadge from './StatusBadge'

const activity = [

  {
    tool: 'database.read',
    decision: 'ALLOW',
    risk: 'LOW',
    text:
      'Read approved sales summary'
  },

  {
    tool: 'report.write',
    decision: 'ALLOW',
    risk: 'MEDIUM',
    text:
      'Create report in designated folder'
  },

  {
    tool: 'send.report',
    decision: 'ESCALATE',
    risk: 'HIGH',
    text:
      'External destination requires approval'
  },

  {
    tool: 'database.delete',
    decision: 'BLOCK',
    risk: 'CRITICAL',
    text:
      'Delete operation is outside role permissions'
  }
]

export default function OverviewTab({
  go
}) {

  return (

    <div className="stack">

      <section className="hero-card">

        <div>

          <div className="eyebrow">
            RUNTIME SECURITY CONTROL PLANE
          </div>

          <h1>
            Agent Permission Governor
          </h1>

          <p>
            Dynamic runtime authorization
            for AI-agent actions using least
            privilege, risk assessment,
            human approval and
            tamper-evident auditing.
          </p>

        </div>

        <div className="hero-status">

          <div className="pulse-ring">
            ✓
          </div>

          <strong>
            Governor Ready
          </strong>

          <small>
            Local execution environment
          </small>

        </div>

      </section>

      <section className="context-strip">

        <div>
          <span>Agent</span>
          <strong>
            demo-data-analyst
          </strong>
        </div>

        <div>
          <span>Role</span>
          <strong>
            data_analyst
          </strong>
        </div>

        <div>
          <span>Task</span>
          <strong>
            sales-report-001
          </strong>
        </div>

        <div>
          <span>Policy</span>
          <strong>
            Least Privilege
          </strong>
        </div>

      </section>

      <section className="metrics">

        <Metric
          value="24"
          label="Actions Evaluated"
        />

        <Metric
          value="16"
          label="Allowed"
          tone="green"
        />

        <Metric
          value="5"
          label="Blocked"
          tone="red"
        />

        <Metric
          value="3"
          label="Pending Approval"
          tone="amber"
        />

      </section>

      <div className="two-column">

        <section className="card">

          <div className="section-heading">

            <div>
              <div className="eyebrow">
                LIVE ACTIVITY
              </div>

              <h2>
                Governor Decisions
              </h2>
            </div>

            <button
              className="text-btn"
              onClick={() => go('actions')}
            >
              View all →
            </button>

          </div>

          <div className="activity-list">

            {activity.map(
              (item, index) => (

                <div
                  className="activity-row"
                  key={index}
                >

                  <div
                    className={
                      `activity-icon
                      ${item.decision.toLowerCase()}`
                    }
                  >
                    {item.decision ===
                    'ALLOW'
                      ? '✓'
                      : item.decision ===
                        'BLOCK'
                        ? '×'
                        : '!'}
                  </div>

                  <div className="activity-main">

                    <strong>
                      {item.tool}
                    </strong>

                    <span>
                      {item.text}
                    </span>

                  </div>

                  <div className="activity-side">

                    <StatusBadge
                      status={item.decision}
                      size="small"
                    />

                    <StatusBadge
                      status={item.risk}
                      size="small"
                    />

                  </div>

                </div>
              )
            )}

          </div>

        </section>

        <section className="card">

          <div className="section-heading">

            <div>

              <div className="eyebrow">
                POLICY PIPELINE
              </div>

              <h2>
                Runtime Flow
              </h2>

            </div>

          </div>

          <div className="pipeline">

            {[
              ['01', 'Tier 0',
                'Validation & authorization'],

              ['02', 'Tier 1',
                'Context & risk'],

              ['03', 'Tier 2',
                'Semantic assistance'],

              ['04', 'Decision',
                'ALLOW / BLOCK / ESCALATE'],

              ['05', 'Tier 3',
                'Restricted enforcement'],
            ].map(
              ([num, title, text],
              index) => (

                <div
                  className="pipeline-step"
                  key={title}
                >

                  <div className="pipeline-num">
                    {num}
                  </div>

                  <div>
                    <strong>
                      {title}
                    </strong>

                    <span>
                      {text}
                    </span>
                  </div>

                  {index < 4 &&
                    <div className="pipeline-arrow">
                      →
                    </div>
                  }

                </div>
              )
            )}

          </div>

        </section>

      </div>

      <section className="quick-actions">

        <button
          onClick={() => go('agent')}
        >
          ⚡
          <div>
            <strong>
              Evaluate Action
            </strong>

            <small>
              Send an agent action
              to the governor
            </small>
          </div>
        </button>

        <button
          onClick={() => go('approvals')}
        >
          !
          <div>
            <strong>
              Review Approvals
            </strong>

            <small>
              Inspect high-risk
              pending actions
            </small>
          </div>
        </button>

        <button
          onClick={() => go('audit')}
        >
          ◈
          <div>
            <strong>
              Audit Ledger
            </strong>

            <small>
              Verify the
              audit chain
            </small>
          </div>
        </button>

      </section>

    </div>
  )
}

function Metric({
  value,
  label,
  tone = ''
}) {

  return (

    <div
      className={`metric ${tone}`}
    >

      <strong>{value}</strong>

      <span>{label}</span>

    </div>
  )
}