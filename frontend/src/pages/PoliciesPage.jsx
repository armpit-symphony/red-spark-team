import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { api } from '../lib/api';

const joinLines = (items = []) => items.join('\n');
const splitLines = (value) => value.split('\n').map((item) => item.trim()).filter(Boolean);

export default function PoliciesPage() {
  const [form, setForm] = useState({ passive_rules: '', deep_mode_requirements: '', deep_mode_consent_token: '', export_requires_review: true, secret_redaction_enabled: true, deny_by_default_egress: true });

  useEffect(() => {
    api.get('/policies')
      .then((data) => setForm({ ...data, passive_rules: joinLines(data.passive_rules), deep_mode_requirements: joinLines(data.deep_mode_requirements) }))
      .catch((error) => toast.error(error.message));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      await api.put('/policies', { ...form, passive_rules: splitLines(form.passive_rules), deep_mode_requirements: splitLines(form.deep_mode_requirements) });
      toast.success('Policies updated');
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="stack" data-testid="policies-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Fail-Closed Rules</div>
          <h1 className="page-title" data-testid="policies-page-title">Policy gates keep the platform defensive</h1>
          <p className="page-subtitle" data-testid="policies-page-subtitle">Exploratory mode stays scoped and passive. Consent-gated mode stays visually isolated, token protected, and review controlled.</p>
        </div>
      </header>

      <div className="mode-alert" data-testid="deep-mode-warning-banner">
        Deep mode requires a written authorization trail, runtime consent token, and human review before export.
      </div>

      <form className="form-shell" onSubmit={handleSubmit} data-testid="policy-form">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Control Flags</div>
            <h2 className="panel-title">Edit active policy doctrine</h2>
          </div>
          <Button type="submit" variant="danger" data-testid="policy-form-submit-button">Save policies</Button>
        </div>
        <div className="field-grid" style={{ marginTop: 16 }}>
          <div className="field"><label className="field-label">Deep mode token</label><Input value={form.deep_mode_consent_token} onChange={(e) => setForm({ ...form, deep_mode_consent_token: e.target.value })} data-testid="deep-mode-token-input" required /></div>
          <div className="field"><label className="field-label">Booleans</label><div className="stack-sm"><label data-testid="policy-export-review-option"><input type="checkbox" checked={form.export_requires_review} onChange={(e) => setForm({ ...form, export_requires_review: e.target.checked })} /> Require human review before export</label><label data-testid="policy-secret-redaction-option"><input type="checkbox" checked={form.secret_redaction_enabled} onChange={(e) => setForm({ ...form, secret_redaction_enabled: e.target.checked })} /> Enforce secret redaction</label><label data-testid="policy-deny-egress-option"><input type="checkbox" checked={form.deny_by_default_egress} onChange={(e) => setForm({ ...form, deny_by_default_egress: e.target.checked })} /> Deny by default network egress</label></div></div>
        </div>
        <div className="field-stack"><label className="field-label">Passive rules</label><Textarea value={form.passive_rules} onChange={(e) => setForm({ ...form, passive_rules: e.target.value })} data-testid="passive-rules-textarea" /></div>
        <div className="field-stack"><label className="field-label">Deep mode requirements</label><Textarea value={form.deep_mode_requirements} onChange={(e) => setForm({ ...form, deep_mode_requirements: e.target.value })} data-testid="deep-requirements-textarea" /></div>
      </form>
    </div>
  );
}
