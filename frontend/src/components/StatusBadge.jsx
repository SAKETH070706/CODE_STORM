const labels = {
  ALLOW: 'ALLOW',
  BLOCK: 'BLOCK',
  ESCALATE: 'ESCALATE',

  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',

  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',

  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
  CRITICAL: 'CRITICAL',
}

export default function StatusBadge({
  status,
  size = 'normal'
}) {

  const value =
    String(status || 'UNKNOWN')
      .toUpperCase()

  return (
    <span
      className={
        `status-badge-pill
        status-${value.toLowerCase()}
        ${size === 'small' ? 'small' : ''}`
      }
    >
      {labels[value] || value}
    </span>
  )
}