import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { StatusBadge } from '../components/common/StatusBadge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { api } from '../lib/api';

const initialForm = { target_id: '', mode: 'exploratory', objective: '', scope_notes: '', consent_token: '' };

export default function AuditRunsPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [targets, setTargets] = useState([]);
  const [form, setForm] = useState(initialForm);

  const loadPage = useCallback(async () => {
    const [runData, targetData] = await Promise.all([api.get('/runs'), api.get('/targets')]);
    setRuns(runData);
    setTargets(targetData);
    if (!form.target_id && targetData[0]?.id) {
      setForm((previous) => ({ ...previous, target_id: targetData[0].id }));
    }
  }, [form.target_id]);

  useEffect(() => {
    loadPage().catch((error) => toast.error(error.message));
  }, [loadPage]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const bundle = await api.post('/runs', form);
      toast.success('Run created');
      navigate(`/audit-runs/${bundle.run.id}`);
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="stack" data-testid="audit-runs-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Workflow Orchestrator</div>
          <h1 className="page-title" data-testid="audit-runs-page-title">Start a governed audit run</h1>
          <p className="page-subtitle" data-testid="audit-runs-page-subtitle">Each run keeps task sequencing, evidence sections, and draft reporting isolated for easier reading and copy-forward work.</p>
        </div>
      </header>

      <form className="form-shell" onSubmit={handleSubmit} data-testid="audit-run-form">
        <div className="panel-header">
          <div>
            <div className="eyebrow">New Run</div>
            <h2 className="panel-title">Create workflow</h2>
          </div>
          <Button type="submit" variant={form.mode === 'consent_gated' ? 'danger' : 'primary'} data-testid="audit-run-submit-button">Start run</Button>
        </div>
        <div className="field-grid" style={{ marginTop: 16 }}>
          <div className="field"><label className="field-label">Target</label><select className="select" value={form.target_id} onChange={(e) => setForm({ ...form, target_id: e.target.value })} data-testid="audit-run-target-select">{targets.map((target) => <option key={target.id} value={target.id}>{target.name}</option>)}</select></div>
          <div className="field"><label className="field-label">Mode</label><select className="select" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })} data-testid="audit-run-mode-select"><option value="exploratory">Exploratory</option><option value="consent_gated">Consent gated</option></select></div>
        </div>
        {form.mode === 'consent_gated' ? <div className="mode-alert" data-testid="audit-run-deep-warning">Consent-gated mode is elevated. Enter the current runtime token exactly before launching.</div> : null}
        <div className="field-stack"><label className="field-label">Objective</label><Input value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} data-testid="audit-run-objective-input" required /></div>
        <div className="field-stack"><label className="field-label">Scope notes</label><Textarea value={form.scope_notes} onChange={(e) => setForm({ ...form, scope_notes: e.target.value })} data-testid="audit-run-scope-notes-textarea" /></div>
        {form.mode === 'consent_gated' ? <div className="field-stack"><label className="field-label">Consent token</label><Input value={form.consent_token} onChange={(e) => setForm({ ...form, consent_token: e.target.value })} data-testid="audit-run-consent-token-input" required /></div> : null}
      </form>

      <section className="table-shell" data-testid="audit-run-table-shell">
        <div className="table-header"><div><div className="eyebrow">History</div><h2 className="panel-title">Run registry</h2></div></div>
        <div className="table-wrap">
          <table className="table" data-testid="audit-runs-table">
            <thead><tr><th>Target</th><th>Mode</th><th>Status</th><th>Objective</th><th>Updated</th></tr></thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} data-testid={`audit-run-row-${run.id}`}>
                  <td><Link to={`/audit-runs/${run.id}`} data-testid={`audit-run-link-${run.id}`}>{run.target_name}</Link><div className="cell-subtle mono">{run.id.slice(0, 8)}</div></td>
                  <td><StatusBadge value={run.mode} testId={`audit-run-mode-${run.id}`} /></td>
                  <td><span className="badge" data-testid={`audit-run-status-${run.id}`}>{run.status}</span></td>
                  <td data-testid={`audit-run-objective-${run.id}`}>{run.objective}</td>
                  <td className="mono" data-testid={`audit-run-updated-${run.id}`}>{new Date(run.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
