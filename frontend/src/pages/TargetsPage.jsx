import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../lib/api';

const initialForm = { name: '', target_type: 'webapp', locator: '', scope_limit: '', notes: '', exploratory: true, consent_gated: false };

export default function TargetsPage() {
  const [targets, setTargets] = useState([]);
  const [form, setForm] = useState(initialForm);

  const loadTargets = () => api.get('/targets').then(setTargets).catch((error) => toast.error(error.message));

  useEffect(() => {
    loadTargets();
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const allowed_modes = [form.exploratory && 'exploratory', form.consent_gated && 'consent_gated'].filter(Boolean);
      await api.post('/targets', { ...form, allowed_modes });
      setForm(initialForm);
      toast.success('Target added');
      loadTargets();
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="stack" data-testid="targets-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Target Registry</div>
          <h1 className="page-title" data-testid="targets-page-title">Scope every target before any run begins</h1>
          <p className="page-subtitle" data-testid="targets-page-subtitle">Each record defines the locator, allowed modes, and the exact boundaries your workflows must respect.</p>
        </div>
      </header>

      <form className="form-shell" onSubmit={handleSubmit} data-testid="target-form">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Add Target</div>
            <h2 className="panel-title">Create a scoped asset record</h2>
          </div>
          <Button type="submit" variant="primary" data-testid="target-form-submit-button">Save target</Button>
        </div>
        <div className="field-grid" style={{ marginTop: 16 }}>
          <div className="field"><label className="field-label">Name</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="target-name-input" required /></div>
          <div className="field"><label className="field-label">Type</label><select className="select" value={form.target_type} onChange={(e) => setForm({ ...form, target_type: e.target.value })} data-testid="target-type-select"><option value="webapp">Webapp</option><option value="repo">Repo</option><option value="script">Script</option><option value="service">Service</option></select></div>
          <div className="field"><label className="field-label">Locator</label><Input value={form.locator} onChange={(e) => setForm({ ...form, locator: e.target.value })} data-testid="target-locator-input" required /></div>
          <div className="field"><label className="field-label">Allowed modes</label><div className="button-row"><label data-testid="target-mode-exploratory-option"><input type="checkbox" checked={form.exploratory} onChange={(e) => setForm({ ...form, exploratory: e.target.checked })} /> Exploratory</label><label data-testid="target-mode-consent-option"><input type="checkbox" checked={form.consent_gated} onChange={(e) => setForm({ ...form, consent_gated: e.target.checked })} /> Consent gated</label></div></div>
        </div>
        <div className="field-stack"><label className="field-label">Scope limit</label><Textarea value={form.scope_limit} onChange={(e) => setForm({ ...form, scope_limit: e.target.value })} data-testid="target-scope-limit-textarea" required /></div>
        <div className="field-stack"><label className="field-label">Notes</label><Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} data-testid="target-notes-textarea" /></div>
      </form>

      <section className="table-shell" data-testid="targets-table-shell">
        <div className="table-header">
          <div>
            <div className="eyebrow">Registry</div>
            <h2 className="panel-title">Tracked targets</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="table" data-testid="targets-table">
            <thead>
              <tr><th>Name</th><th>Locator</th><th>Scope</th><th>Modes</th><th>Last audit</th></tr>
            </thead>
            <tbody>
              {targets.map((target) => (
                <tr key={target.id} data-testid={`target-row-${target.id}`}>
                  <td><div data-testid={`target-name-${target.id}`}>{target.name}</div><div className="cell-subtle">{target.target_type}</div></td>
                  <td className="mono" data-testid={`target-locator-${target.id}`}>{target.locator}</td>
                  <td data-testid={`target-scope-${target.id}`}>{target.scope_limit}</td>
                  <td><div className="button-row">{target.allowed_modes.map((mode) => <StatusBadge key={mode} value={mode} testId={`target-mode-${target.id}-${mode}`} />)}</div></td>
                  <td className="mono" data-testid={`target-last-audit-${target.id}`}>{target.last_audit_at ? new Date(target.last_audit_at).toLocaleString() : 'Not yet'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
