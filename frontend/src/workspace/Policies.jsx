import React, { useState } from 'react';
import { Form, Field, Choice, Badge, Details } from './shared';
import { options, pretty } from './sharedValues';
import { diffRules, parseRules, safeStorage, DRAFT_PREFIX } from '../workspaceClient';

export default function Policies({
  sources,
  policies,
  jobs,
  registry,
  overview,
  api,
  work,
  can,
  busy,
  session,
}) {
  // Unsaved edits are mirrored to sessionStorage, keyed by user and policy, so an expired session
  // does not lose them. They are discarded on save, reload of the version, or explicit sign-out.
  const who = session?.principal_id || '';
  const selKey = `${DRAFT_PREFIX}sel_${who}`;
  const editKey = id => `${DRAFT_PREFIX}editor_${who}_${id}`;
  const [selectedId, setSelectedId] = useState(() => (who ? safeStorage.get(selKey) : ''));
  const [customEditor, setCustomEditor] = useState(null);

  const selected = (selectedId && policies.find(p => p.id === selectedId)) || policies[0] || null;
  const stored = who && selected ? safeStorage.get(editKey(selected.id)) : '';
  const editor =
    customEditor !== null
      ? customEditor
      : stored
      ? stored
      : selected?.data?.rules
      ? pretty(selected.data.rules)
      : '[]';

  const { rules, error: editorError } = parseRules(editor);
  const dirty = !!selected && (!!editorError || JSON.stringify(rules) !== JSON.stringify(selected.data.rules));
  const source = sources.find(s => s.id === rules[0]?.source?.source_id) || sources[0];
  const active = policies.find(p => p.id === overview?.active_policy_id);

  function edit(p) {
    if (!p?.data) throw new Error('Policy could not be loaded. Refresh the policy list.');
    setSelectedId(p.id);
    setCustomEditor(null);
    if (who) { safeStorage.set(selKey, p.id); safeStorage.set(editKey(p.id), ''); }
  }

  async function saveDraft() {
    await work(async () => {
      const saved = await api('/policies', {
        id: selected.id,
        name: selected.name,
        expected_revision: selected.data.revision,
        rules,
      });
      edit(saved);
    }, 'Draft saved');
  }

  async function saveAndValidate() {
    await work(async () => {
      if (dirty) {
        const saved = await api('/policies', {
          id: selected.id,
          name: selected.name,
          expected_revision: selected.data.revision,
          rules,
        });
        setSelectedId(saved.id);
        if (who) safeStorage.set(editKey(saved.id), '');
      }
      const val = await api(`/policies/${selected.id}/validate`, {});
      edit(val);
    }, 'Policy validated successfully');
  }

  async function publishPolicy() {
    await work(async () => {
      if (dirty || selected.state === 'DRAFT') {
        if (editorError) throw new Error('Cannot publish: ' + editorError);
        const saved = await api('/policies', {
          id: selected.id,
          name: selected.name,
          expected_revision: selected.data.revision,
          rules,
        });
        setSelectedId(saved.id);
        if (who) safeStorage.set(editKey(saved.id), '');
        await api(`/policies/${selected.id}/validate`, {});
      }
      const p = await api(`/policies/${selected.id}/publish`, {
        expected_active_policy_id: overview?.active_policy_id || null,
      });
      edit(p);
    }, 'Policy published successfully');
  }

  return (
    <>
      <section className="grid">
        {can('sources') && (
          <>
            <Form
              title="Upload company policy"
              onSubmit={form =>
                work(async () => {
                  const file = form.get('file');
                  if (file?.size > 2 * 1024 * 1024) {
                    throw new Error('Policy files must be 2 MiB or smaller.');
                  }
                  const s = await api('/sources/upload', form);
                  const all = await api('/policies');
                  if (s?.draft_id) {
                    const draft = all.find(p => p.id === s.draft_id);
                    if (draft) edit(draft);
                  }
                }, 'Source extracted and draft selected')
              }
            >
              <Field
                label="PDF, Markdown or text · maximum 2 MiB"
                type="file"
                name="file"
                accept=".pdf,.md,.txt"
                required
              />
              <Choice label="Revision of an existing source (optional)" name="previous_id">
                <option value="">New source</option>
                {options(sources)}
              </Choice>
              <button disabled={busy}>Upload source</button>
            </Form>

            <Form
              title="Import approved policy URL"
              onSubmit={form =>
                work(() => api('/sources/url', Object.fromEntries(form)), 'URL imported as draft evidence')
              }
            >
              <Field label="HTTPS URL on an administrator-allowed host" type="url" name="url" required />
              <button disabled={busy}>Import URL</button>
            </Form>
          </>
        )}
      </section>

      <section className="panel">
        <h2>Policy versions</h2>
        {policies.length ? (
          policies.map(p => (
            <button
              className={`list-item ${selected?.id === p.id ? 'active' : ''}`}
              key={p.id}
              onClick={() => edit(p)}
            >
              <span>
                {p.name}
                <small>
                  {p.id.slice(0, 8)} · revision {p.data.revision}
                </small>
              </span>
              <Badge value={p.state} />
            </button>
          ))
        ) : (
          <p>Upload a source to begin. No published policy means deny by default.</p>
        )}
      </section>

      {can('drafts') && sources.length > 0 && (
        <Form
          title="Propose rules without a cloud model"
          onSubmit={form =>
            work(async () => {
              if (!selected) throw new Error('Upload a policy source first to create a draft');
              const task = registry.tasks.find(t => t.id === form.get('task'));
              if (!task) throw new Error('Choose a task');
              const resources = {};
              for (const c of registry.connectors) {
                const tool = {
                  demo_sales: 'database.read',
                  report_storage: 'report.create',
                  simulated_delivery: 'report.send',
                }[c.data.kind];
                if (tool && task.data.resources.includes(c.id)) resources[tool] = c.id;
              }
              await api('/compilations', {
                source_id: form.get('source'),
                policy_id: selected.id,
                mode: 'manual',
                configuration: {
                  role: form.get('role'),
                  task_id: task.id,
                  resources,
                  reviewer_group: form.get('group'),
                  destinations: ['review@example.test'],
                },
              });
              const refreshed = await api('/policies');
              const fresh = refreshed.find(p => p.id === selected.id);
              if (fresh) edit(fresh);
            }, 'Suggestions generated and loaded into the editor')
          }
        >
          <div className="grid">
            <Choice label="Source" name="source">
              {options(sources)}
            </Choice>
            <Choice label="Task" name="task" required>
              <option value="">Choose task</option>
              {options(registry.tasks)}
            </Choice>
            <Field label="Business role" name="role" defaultValue="data_analyst" required />
            <Choice label="Reviewer group" name="group">
              {options(registry.groups)}
            </Choice>
          </div>
          <button disabled={busy || !selected}>
            {busy ? 'Generating draft suggestions...' : 'Generate draft suggestions'}
          </button>
          <p className="muted">Verify every suggestion, then resolve its assumptions in the editor.</p>
          {jobs.slice(0, 3).map(j => (
            <p key={j.id}>
              {j.id.slice(0, 8)} <Badge value={j.state} />
              {j.data.error}
            </p>
          ))}
        </Form>
      )}

      {selected && (
        <section className="panel">
          <div className="row">
            <h2>{selected.name}</h2>
            <Badge value={selected.state} />
            <button
              className="secondary"
              onClick={() => edit(policies.find(p => p.id === selected.id) || selected)}
            >
              Reload selected version
            </button>
          </div>
          <div className="split">
            <div>
              <h3>Source evidence</h3>
              {source ? (
                <>
                  <p>
                    {source.name} · revision {source.data.revision}
                  </p>
                  {source.data.segments.map(s => (
                    <blockquote key={s.index}>
                      <small>{s.reference}</small>
                      <p>{s.text}</p>
                    </blockquote>
                  ))}
                </>
              ) : (
                <p>Select a source for citations.</p>
              )}
            </div>
            <div>
              <label>
                Structured rules
                <textarea
                  aria-label="Structured rules"
                  rows={25}
                  value={editor}
                  readOnly={!can('drafts') || !['DRAFT', 'VALIDATED'].includes(selected.state)}
                  onChange={e => { setCustomEditor(e.target.value); if (who) safeStorage.set(editKey(selected.id), e.target.value); }}
                />
              </label>
              <p className="muted">
                Explicit role, tool, resource, task, constraints, decision, reviewer group and source citation. No
                executable expressions.
              </p>
            </div>
          </div>
          {editorError && (
            <p className="error" role="alert">
              {editorError}
            </p>
          )}
          {dirty && <p className="notice">Unsaved changes in editor.</p>}
          {selected.data.validation_errors?.length > 0 && (
            <ul className="error">
              {selected.data.validation_errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
          <div className="row" style={{ marginTop: '12px', gap: '8px' }}>
            {can('drafts') && (
              <>
                <button
                  disabled={busy || !!editorError}
                  onClick={saveDraft}
                >
                  {busy ? 'Saving...' : 'Save draft'}
                </button>
                <button
                  disabled={busy || !!editorError}
                  onClick={saveAndValidate}
                >
                  {busy ? 'Validating...' : 'Validate saved draft'}
                </button>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    work(async () => {
                      edit(await api(`/policies/${selected.id}/clone`, {}));
                    }, 'Cloned as new draft')
                  }
                >
                  {busy ? 'Cloning...' : 'Clone as new draft'}
                </button>
              </>
            )}
            {can('publish') && (
              <button
                disabled={busy || !!editorError}
                onClick={publishPolicy}
              >
                {busy ? 'Publishing...' : 'Publish validated policy'}
              </button>
            )}
          </div>
          <h3>Diff against active policy</h3>
          {diffRules(active?.data.rules, rules).map(d => (
            <details key={d.id}>
              <summary>
                {d.status}: {d.id}
              </summary>
              <div className="split">
                <Details value={d.before || 'Absent'} />
                <Details value={d.after || 'Absent'} />
              </div>
            </details>
          ))}
        </section>
      )}
    </>
  );
}
