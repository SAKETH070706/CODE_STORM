import React from 'react';

/** Floating notifications: fixed position so the outcome of an action is visible wherever the button was. */
export default function ToastHost({ toasts, dismiss }) {
  return <div className="toast-host" role="region" aria-label="Notifications">
    {toasts.map(t => <div key={t.id} className={`toast toast-${t.type}`} role={t.type === 'error' ? 'alert' : 'status'}>
      <span className="toast-message">{t.message}</span>
      {t.action && <button type="button" className="toast-action" onClick={() => { t.action.run(); dismiss(t.id); }}>{t.action.label}</button>}
      <button type="button" className="toast-close" aria-label="Dismiss notification" onClick={() => dismiss(t.id)}>×</button>
    </div>)}
  </div>;
}
