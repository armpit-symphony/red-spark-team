import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { api } from '../lib/api';

export default function AuditLogPage() {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    api.get('/audit-log').then(setEntries).catch((error) => toast.error(error.message));
  }, []);

  return (
    <div className="stack" data-testid="audit-log-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Chronological Feed</div>
          <h1 className="page-title" data-testid="audit-log-page-title">Track every admin action in a terminal-style timeline</h1>
          <p className="page-subtitle" data-testid="audit-log-page-subtitle">The log keeps policy edits, provider changes, section saves, and analysis requests visible in one place.</p>
        </div>
      </header>

      <section className="timeline" data-testid="audit-log-timeline">
        {entries.map((entry) => (
          <article key={entry.id} className="timeline-item" data-testid={`audit-log-entry-${entry.id}`}>
            <div className="timeline-item__time" data-testid={`audit-log-time-${entry.id}`}>{new Date(entry.created_at).toLocaleString()}</div>
            <div className="mono" style={{ marginTop: 10 }} data-testid={`audit-log-action-${entry.id}`}>{entry.action}</div>
            <p className="panel-copy" data-testid={`audit-log-details-${entry.id}`}>{entry.details}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
