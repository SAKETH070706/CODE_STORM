import React, { useState, useRef } from 'react';
import { Form, Field, Choice, Badge, Details } from './shared';
import { options } from './sharedValues';

export default function Registry({ registry, members, api, work, can, busy, _setDetail, session }) {
  const [key, setKey] = useState(null); // { agentId, key }
  const [copiedKey, setCopiedKey] = useState(false);
  const [submitting, setSubmitting] = useState('');
  const [testResult, setTestResult] = useState(null); // { connectorId, data }
  const lock = useRef(false);
  const keyBannerRef = useRef(null);
  const testResultRef = useRef(null);

  const setKeyAndScroll = (val) => {
    setKey(val);
    setCopiedKey(false);
    if (val) {
      setTimeout(() => {
        keyBannerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);
    }
  };

  const setTestResultAndScroll = (val) => {
    setTestResult(val);
    if (val) {
      setTimeout(() => {
        testResultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);
    }
  };

  const submitAction = async (actionKey, fn, successMsg) => {
    if (lock.current || busy) return { ok: false };
    lock.current = true;
    setSubmitting(actionKey);
    try {
      return await work(fn, successMsg);
    } finally {
      lock.current = false;
      setSubmitting('');
    }
  };

  return (
    <>
      {/* ─────────────────────────────────────────────────────────────
          SECTION 1: CONNECTORS (FORM ON LEFT, LIVE RESULTS ON RIGHT)
      ───────────────────────────────────────────────────────────── */}
      <section className="grid" style={{ alignItems: 'start', marginBottom: '24px' }}>
        {can('connectors') && (
          <Form
            title="1. Connect supported resource"
            onSubmit={f =>
              submitAction(
                'connector',
                () =>
                  api('/connectors', {
                    name: f.get('name'),
                    kind: f.get('kind'),
                    destinations: f.get('kind') === 'simulated_delivery' ? ['review@example.test'] : [],
                  }),
                'Resource connected successfully'
              )
            }
          >
            <Field label="Display name" name="name" placeholder="e.g. Sales DB" required />
            <Choice label="Connector type" name="kind">
              <option value="demo_sales">Demo sales database</option>
              <option value="demo_support">Demo support database</option>
              <option value="report_storage">Protected report artifacts</option>
              <option value="simulated_delivery">Simulated delivery only</option>
            </Choice>
            <button disabled={submitting === 'connector'}>
              {submitting === 'connector' ? 'Connecting resource...' : 'Connect resource'}
            </button>
          </Form>
        )}

        <div className="panel">
          <h2>Connected resources ({registry.connectors.length})</h2>
          {registry.connectors.length ? (
            registry.connectors.map(c => (
              <article
                className="record"
                key={c.id}
                style={{
                  marginBottom: '12px',
                  padding: '12px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0 }}>{c.name}</h3>
                  <small style={{ color: '#64748b' }}>{c.id.slice(0, 10)}…</small>
                </div>
                <p style={{ margin: '4px 0 8px 0', fontSize: '13px', color: '#475569' }}>
                  {c.data.kind === 'simulated_delivery'
                    ? 'Simulated delivery only'
                    : c.data.kind.startsWith('demo_')
                    ? 'Demo SQL connector'
                    : 'Local artifact storage'}
                </p>

                {can('connectors') && (
                  <div>
                    <button
                      className="secondary"
                      style={{ padding: '4px 10px', fontSize: '13px' }}
                      disabled={submitting === `test-${c.id}`}
                      onClick={() =>
                        submitAction(
                          `test-${c.id}`,
                          async () => {
                            const res = await api(`/connectors/${c.id}/test`, {});
                            setTestResultAndScroll({ connectorId: c.id, data: res });
                          },
                          'Connection test completed'
                        )
                      }
                    >
                      {submitting === `test-${c.id}` ? 'Testing connection...' : 'Test connection'}
                    </button>
                  </div>
                )}

                {/* INLINE TEST RESULT RIGHT UNDER THE CONNECTOR */}
                {testResult && testResult.connectorId === c.id && (
                  <div
                    ref={testResultRef}
                    style={{
                      marginTop: '10px',
                      padding: '12px',
                      background: '#ffffff',
                      border: '1px solid #cbd5e1',
                      borderRadius: '6px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <strong style={{ fontSize: '13px', color: 'var(--text-strong, #0f172a)' }}>✓ Connection test output:</strong>
                      <button
                        className="secondary"
                        style={{ padding: '2px 8px', fontSize: '12px' }}
                        onClick={() => setTestResult(null)}
                      >
                        Close
                      </button>
                    </div>
                    <Details value={testResult.data} />
                  </div>
                )}
              </article>
            ))
          ) : (
            <p className="muted">No resources connected yet. Add Sales DB, Report Storage, or Outbox using the form on the left.</p>
          )}
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          SECTION 2: AGENTS (FORM ON LEFT, LIVE RESULTS ON RIGHT)
      ───────────────────────────────────────────────────────────── */}
      <section className="grid" style={{ alignItems: 'start', marginBottom: '24px' }}>
        {can('agents') && (
          <Form
            title="2. Register an agent"
            onSubmit={f =>
              submitAction(
                'agent',
                () => api('/agents', Object.fromEntries(f)),
                'Agent registered successfully'
              )
            }
          >
            <Field label="Agent name" name="name" placeholder="e.g. Financial Analyst Agent" required />
            <Field
              label="Business role"
              name="role"
              defaultValue="data_analyst"
              pattern="[a-z][-a-z0-9_]{1,49}"
              required
            />
            <button disabled={submitting === 'agent'}>
              {submitting === 'agent' ? 'Registering agent...' : 'Register agent'}
            </button>
          </Form>
        )}

        <div className="panel">
          <h2>Registered agents ({registry.agents.length})</h2>
          {registry.agents.length ? (
            registry.agents.map(a => (
              <article
                className="record"
                key={a.id}
                style={{
                  marginBottom: '12px',
                  padding: '12px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0 }}>{a.name}</h3>
                  <Badge value={a.state} />
                </div>
                <p style={{ margin: '4px 0 8px 0', fontSize: '13px', color: '#475569' }}>
                  Role: <code>{a.data.role}</code> · ID: <small>{a.id.slice(0, 10)}…</small>
                </p>

                {can('agents') && (
                  <div className="row" style={{ gap: '8px', marginTop: '6px' }}>
                    <button
                      disabled={submitting === a.id || a.state !== 'ACTIVE'}
                      style={{ padding: '4px 10px', fontSize: '13px' }}
                      onClick={() =>
                        submitAction(
                          a.id,
                          async () => {
                            const generated = await api(`/agents/${a.id}/key`, {});
                            setKeyAndScroll({ agentId: a.id, key: generated.key });
                          },
                          'Key generated securely'
                        )
                      }
                    >
                      {submitting === a.id ? 'Generating key...' : 'Generate key'}
                    </button>
                    <button
                      className="danger"
                      style={{ padding: '4px 10px', fontSize: '13px' }}
                      disabled={submitting === `revoke-${a.id}` || a.state !== 'ACTIVE'}
                      onClick={() =>
                        submitAction(
                          `revoke-${a.id}`,
                          () => api(`/agents/${a.id}/revoke`, {}),
                          'Agent and keys revoked'
                        )
                      }
                    >
                      Revoke
                    </button>
                  </div>
                )}

                {/* INLINE GENERATED KEY BANNER RIGHT INSIDE THE AGENT CARD */}
                {key && key.agentId === a.id && (
                  <div
                    ref={keyBannerRef}
                    className="secret"
                    style={{
                      marginTop: '12px',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1.5px solid var(--accent, #6366f1)',
                      background: 'rgba(99, 102, 241, 0.05)',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <h4 style={{ margin: 0, color: 'var(--text-strong, #0f172a)' }}>🔑 Generated Agent Key:</h4>
                      <span className="badge" style={{ fontSize: '11px', background: '#e0e7ff', color: '#3730a3' }}>Display Once</span>
                    </div>
                    <p className="muted" style={{ margin: '0 0 8px 0', fontSize: '12px' }}>
                      Stored only as SHA-256 hash. Copy and save it now:
                    </p>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <code style={{ flex: 1, padding: '8px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '4px', wordBreak: 'break-all', fontSize: '13px', fontWeight: 600 }}>
                        {key.key}
                      </code>
                      <button
                        style={{ padding: '6px 14px', whiteSpace: 'nowrap' }}
                        onClick={() => {
                          navigator.clipboard?.writeText(key.key);
                          setCopiedKey(true);
                          setTimeout(() => setCopiedKey(false), 2000);
                        }}
                      >
                        {copiedKey ? '✓ Copied!' : 'Copy Key'}
                      </button>
                    </div>
                    <button
                      className="secondary"
                      style={{ marginTop: '8px', padding: '4px 12px', fontSize: '12px' }}
                      onClick={() => setKey(null)}
                    >
                      I have saved it securely
                    </button>
                  </div>
                )}
              </article>
            ))
          ) : (
            <p className="muted">No agents registered yet. Use the form on the left to add an agent.</p>
          )}
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          SECTION 3: GROUPS & TASKS (FORMS ON LEFT, LIVE ASSIGNMENTS ON RIGHT)
      ───────────────────────────────────────────────────────────── */}
      <section className="grid" style={{ alignItems: 'start', marginBottom: '24px' }}>
        <div>
          {can('members') && (
            <Form
              title="3. Create reviewer group"
              onSubmit={f =>
                submitAction(
                  'group',
                  () => api('/groups', Object.fromEntries(f)),
                  'Reviewer group created successfully'
                )
              }
            >
              <Field label="Group name" name="name" defaultValue="Security Reviewers" required />
              <button disabled={submitting === 'group'}>
                {submitting === 'group' ? 'Creating group...' : 'Create group'}
              </button>
            </Form>
          )}

          {can('agents') && (
            <Form
              title="4. Create a scoped task"
              onSubmit={f =>
                submitAction(
                  'task',
                  () =>
                    api('/tasks', {
                      name: f.get('name'),
                      description: f.get('description') || '',
                      roles: f
                        .get('roles')
                        .split(',')
                        .map(s => s.trim()),
                      resources: f.getAll('resources'),
                      agents: f.getAll('agents'),
                    }),
                  'Task and assignments created successfully'
                )
              }
            >
              <Field label="Task name" name="name" defaultValue="sales-report" required />
              <Field label="Description" name="description" placeholder="e.g. Sales Report Generator" />
              <Field
                label="Permitted business roles (comma separated)"
                name="roles"
                defaultValue="data_analyst"
                required
              />
              <div className="grid">
                <Choice label="Resources (Ctrl/Cmd to multi-select)" name="resources" multiple size={4}>
                  {options(registry.connectors)}
                </Choice>
                <Choice label="Assigned agents" name="agents" multiple size={4}>
                  {options(registry.agents)}
                </Choice>
              </div>
              <button disabled={submitting === 'task'}>
                {submitting === 'task' ? 'Creating task...' : 'Create task'}
              </button>
            </Form>
          )}
        </div>

        <div className="panel">
          <h2>Task assignments ({registry.tasks.length})</h2>
          {registry.tasks.length ? (
            registry.tasks.map(t => (
              <article
                className="record"
                key={t.id}
                style={{
                  marginBottom: '12px',
                  padding: '12px',
                  background: '#fbfcfc',
                  border: '1px solid var(--line)',
                  borderRadius: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0 }}>{t.name}</h3>
                  <small>{t.id.slice(0, 10)}…</small>
                </div>
                {t.data?.description && (
                  <p style={{ margin: '2px 0 6px 0', fontSize: '13px', fontWeight: 500, color: 'var(--text-strong, #0f172a)' }}>
                    {t.data.description}
                  </p>
                )}
                <p style={{ margin: '4px 0 8px 0', fontSize: '13px', color: 'var(--muted)' }}>
                  Roles: <code>{t.data.roles.join(', ')}</code> · {t.data.agents.length} agent(s) ·{' '}
                  {t.data.resources.length} resource(s)
                </p>

                {can('agents') && (
                  <Form
                    className="subform"
                    title="Update assignments"
                    onSubmit={f =>
                      submitAction(
                        `task-assign-${t.id}`,
                        () =>
                          api('/tasks', {
                            id: t.id,
                            name: t.name,
                            ...t.data,
                            agents: f.getAll('agents'),
                          }),
                        'Assignment updated successfully'
                      )
                    }
                  >
                    <Choice
                      key={`${t.id}-${(t.data.agents || []).slice().sort().join(',')}`}
                      label="Assigned agents"
                      name="agents"
                      multiple
                      defaultValue={t.data.agents}
                    >
                      {options(registry.agents)}
                    </Choice>
                    <button disabled={submitting === `task-assign-${t.id}`}>
                      {submitting === `task-assign-${t.id}` ? 'Saving...' : 'Save assignments'}
                    </button>
                  </Form>
                )}
              </article>
            ))
          ) : (
            <p className="muted">No tasks defined yet. Create a scoped task using the form on the left.</p>
          )}
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          SECTION 4: WORKSPACE MEMBERSHIP (PROVISION / UPDATE)
      ───────────────────────────────────────────────────────────── */}
      {can('members') && (
        <section className="grid" style={{ alignItems: 'start', marginBottom: '24px' }}>
          <div>
            <Form
              title="5. Provision or update membership"
              onSubmit={f =>
                submitAction(
                  'member',
                  () =>
                    api('/members', {
                      email: f.get('email'),
                      password: f.get('password') || null,
                      permissions: f
                        .get('permissions')
                        .split(',')
                        .map(p => p.trim())
                        .filter(Boolean),
                      groups: f.getAll('groups'),
                    }),
                  'Membership updated successfully'
                )
              }
            >
              <Field label="Email" type="email" name="email" required />
              <Field
                label="Initial password (for a new account only)"
                type="password"
                name="password"
                minLength={12}
                autoComplete="new-password"
              />
              <Field
                label="Workspace permissions (comma separated)"
                name="permissions"
                defaultValue="review,activity,audit"
              />
              <Choice label="Reviewer groups" name="groups" multiple>
                {options(registry.groups)}
              </Choice>
              <p className="muted">
                Available permissions: members, sources, drafts, publish, agents, connectors, review, audit, activity,
                playground.
              </p>
              <button disabled={submitting === 'member'}>
                {submitting === 'member' ? 'Saving membership...' : 'Save membership'}
              </button>
            </Form>
          </div>

          <div className="panel">
            <h2>Workspace members ({members.length})</h2>
            {members.length ? (
              members.map(m => (
                <article
                  className="record"
                  key={m.id}
                  style={{
                    marginBottom: '12px',
                    padding: '12px',
                    background: '#fbfcfc',
                    border: '1px solid var(--line)',
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '14px' }}>{m.email}</strong>
                    <Badge value={m.active ? 'ACTIVE' : 'REVOKED'} />
                  </div>
                  <p style={{ margin: '4px 0 8px 0', fontSize: '12px', color: 'var(--muted)' }}>
                    Permissions: {m.permissions?.length ? m.permissions.join(', ') : 'none'}
                    {m.groups?.length ? ` · Groups: ${m.groups.length}` : ''}
                  </p>
                  {m.active && m.user_id !== session?.principal_id && (
                    <button
                      type="button"
                      className="danger"
                      disabled={submitting === `revoke-member-${m.id}`}
                      onClick={() =>
                        submitAction(
                          `revoke-member-${m.id}`,
                          () => api(`/members/${m.id}/revoke`, {}),
                          `Membership for ${m.email} revoked`
                        )
                      }
                      style={{ fontSize: '12px', padding: '4px 10px' }}
                    >
                      {submitting === `revoke-member-${m.id}` ? 'Revoking...' : `Revoke ${m.email}`}
                    </button>
                  )}
                </article>
              ))
            ) : (
              <p className="muted">No other members in this workspace.</p>
            )}
          </div>
        </section>
      )}
    </>
  );
}
