import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { CopyBlock } from '../components/common/CopyBlock';
import { api } from '../lib/api';

export default function ReportsPage() {
  const [reports, setReports] = useState([]);

  useEffect(() => {
    api.get('/reports').then(setReports).catch((error) => toast.error(error.message));
  }, []);

  return (
    <div className="stack" data-testid="reports-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Draft Output</div>
          <h1 className="page-title" data-testid="reports-page-title">Copy-ready reports stay isolated and readable</h1>
          <p className="page-subtitle" data-testid="reports-page-subtitle">Each report keeps its own markdown body and review flag so you can paste it into your next workflow without extra cleanup.</p>
        </div>
      </header>

      <section className="grid-2">
        {reports.map((report) => (
          <article key={report.id} className="panel" data-testid={`report-card-${report.id}`}>
            <div className="panel-header">
              <div>
                <div className="eyebrow">{report.review_status}</div>
                <h2 className="panel-title" data-testid={`report-title-${report.id}`}>{report.title}</h2>
              </div>
            </div>
            <p className="panel-copy" data-testid={`report-summary-${report.id}`}>{report.executive_summary}</p>
            <CopyBlock title={report.title} content={report.markdown} testId={`report-markdown-${report.id}`} />
          </article>
        ))}
      </section>
    </div>
  );
}
