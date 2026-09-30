import StatusBadge from './StatusBadge'

export default function ActionDetails({
  action,
  onClose
}) {

  if (!action)
    return null

  const args =
    action.arguments ??
    action.arguments_json ??
    {}

  return (

    <div
      className="modal-backdrop"
      onClick={onClose}
    >

      <div
        className="modal-card"
        onClick={e =>
          e.stopPropagation()
        }
      >

        <div className="modal-header">

          <div>

            <div className="eyebrow">
              ACTION DETAILS
            </div>

            <h2>
              {action.action_id ||
                action.id ||
                'Action'}
            </h2>

          </div>

          <button
            className="icon-btn"
            onClick={onClose}
          >
            ×
          </button>

        </div>

        <div className="detail-grid">

          <Detail
            label="Task"
            value={action.task_id}
          />

          <Detail
            label="Agent"
            value={action.agent_id}
          />

          <Detail
            label="Role"
            value={
              action.role ||
              'data_analyst'
            }
          />

          <Detail
            label="Tool"
            value={action.tool}
          />

          <Detail
            label="Resource"
            value={action.resource}
          />

          <Detail
            label="Decision"
            value={
              <StatusBadge
                status={action.decision}
              />
            }
          />

          <Detail
            label="Risk"
            value={`${action.risk_score ?? 0}/100`}
          />

          <Detail
            label="Risk level"
            value={
              <StatusBadge
                status={
                  action.risk_level ||
                  'LOW'
                }
              />
            }
          />

          <Detail
            label="State"
            value={action.state}
          />

          <Detail
            label="Created"
            value={formatDate(
              action.created_at
            )}
          />

        </div>

        <div className="detail-block">

          <span>Arguments</span>

          <pre>
            {formatJson(args)}
          </pre>

        </div>

        <div className="detail-block">

          <span>Reason</span>

          <p className="reason-text">
            {action.reason ||
              'No reason supplied.'}
          </p>

        </div>

      </div>

    </div>
  )
}

function Detail({ label, value }) {

  return (

    <div className="detail-item">

      <span>{label}</span>

      <strong>
        {value ?? '—'}
      </strong>

    </div>
  )
}

function formatJson(value) {

  if (typeof value === 'string') {

    try {

      return JSON.stringify(
        JSON.parse(value),
        null,
        2
      )

    } catch {

      return value
    }
  }

  return JSON.stringify(
    value,
    null,
    2
  )
}

function formatDate(value) {

  if (!value)
    return '—'

  const date =
    new Date(value)

  if (Number.isNaN(
    date.getTime()
  ))
    return String(value)

  return date.toLocaleString()
}