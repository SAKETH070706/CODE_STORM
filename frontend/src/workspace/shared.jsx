import React, { useContext, useRef, useState } from 'react';
import { describeError, isCancelled } from '../workspaceClient';
import {RequestContext,pretty} from './sharedValues';
import RequestProgress from './RequestProgress';
export function Form({ title, children, onSubmit, className = "panel" }) {
  const busy = useContext(RequestContext);
  const lock = useRef(false);
  const [submitting, setSubmitting] = useState(false), [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    if (lock.current || busy) return;
    const form = new FormData(event.currentTarget);
    lock.current = true; setSubmitting(true); setError('');
    try {
      const outcome = await onSubmit(form);
      // work() reports failures by returning them; show the reason right beside the inputs as well as in a toast.
      if (outcome && outcome.ok === false && outcome.error) setError(describeError(outcome.error));
    }
    catch (e) { if (!isCancelled(e)) setError(describeError(e)); }
    finally { lock.current = false; setSubmitting(false); }
    // Keep inputs on both errors and success. Assignment forms must never reset to old defaults.
  }
  return <form className={className} onSubmit={submit} aria-busy={submitting}>
    <h3>{title}</h3><fieldset disabled={busy || submitting} className="form-fields">{children}</fieldset>
    {submitting && <RequestProgress/>}
    {error && <p className="error" role="alert">{error}</p>}
  </form>;
}
export const Field = ({label,...props}) => <label>{label}<input {...props}/></label>;
export const Choice = ({label,children,...props}) => <label>{label}<select aria-label={label} {...props}>{children}</select></label>;
export const Badge = ({value}) => <span className={`badge ${typeof value === 'string' ? value.toLowerCase() : ''}`}>{value}</span>;
export const Details = ({value}) => <pre className="details">{pretty(value)}</pre>;
export class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <section className="panel error" role="alert"><h2>This screen could not be displayed</h2><p>No operation will be retried automatically. You can reopen this screen or reload the application.</p><button type="button" onClick={() => this.setState({failed:false})}>Try this screen again</button><button type="button" onClick={() => location.reload()}>Reload application</button></section>;
  }
}
