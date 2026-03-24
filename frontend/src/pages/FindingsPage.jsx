import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { StatusBadge } from '../components/common/StatusBadge';
import { Input } from '../components/ui/input';
import { api } from '../lib/api';

export default function FindingsPage() {
  const [findings, setFindings] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api.get('/findings').then(setFindings).catch((error) => toast.error(error.message));
  }, []);

  const filteredFindings = useMemo(
    () => findings.filter((finding) => `${finding.title} ${finding.evidence} ${finding.remediation}`.toLowerCase().includes(search.toLowerCase())),
    [findings, search]
  );

  return (
    <div className="stack" data-testid="findings-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Canonical Schema</div>
          <h1 className="page-title" data-testid="findings-page-title">Review normalized findings with confidence and remediation</h1>
          <p className="page-subtitle" data-testid="findings-page-subtitle">Search across titles, evidence notes, and remediation guidance without losing the audit run context.</p>
        </div>
        <div style={{ minWidth: 280 }}>
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search findings" data-testid="findings-search-input" />
        </div>
      </header>

      <section className="grid-2">
        {filteredFindings.map((finding) => (
          <article key={finding.id} className="panel" data-testid={`finding-card-${finding.id}`}>
            <div className="panel-header">
              <div>
                <div className="eyebrow">Finding</div>
                <h2 className="panel-title" data-testid={`finding-title-${finding.id}`}>{finding.title}</h2>
              </div>
              <div className="button-row">
                <StatusBadge value={finding.severity} tone="severity" testId={`finding-severity-${finding.id}`} />
                <span className="badge" data-testid={`finding-confidence-${finding.id}`}>{finding.confidence}</span>
              </div>
            </div>
            <div className="stack-sm" style={{ marginTop: 16 }}>
              <div data-testid={`finding-status-${finding.id}`}><span className="eyebrow">Status</span><div style={{ marginTop: 8 }}>{finding.status}</div></div>
              <div data-testid={`finding-evidence-${finding.id}`}><span className="eyebrow">Evidence</span><p className="panel-copy">{finding.evidence}</p></div>
              <div data-testid={`finding-remediation-${finding.id}`}><span className="eyebrow">Remediation</span><p className="panel-copy">{finding.remediation}</p></div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}