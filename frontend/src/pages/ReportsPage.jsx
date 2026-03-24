import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { CopyBlock } from '../components/common/CopyBlock';
import { Button } from '../components/ui/button';
import { copyToClipboard } from '../lib/clipboard';
import { api } from '../lib/api';

const downloadMarkdown = (filename, markdown) => {
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [approvingReport, setApprovingReport] = useState('');
  const [exportingAction, setExportingAction] = useState('');

  const loadReports = () => api.get('/reports').then(setReports).catch((error) => toast.error(error.message));

  useEffect(() => {
    loadReports();
  }, []);

  const approveReport = async (report) => {
    try {
      setApprovingReport(report.id);
      await api.post(`/reports/${report.id}/approve`, {});
      toast.success('Report approved for export');
      loadReports();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setApprovingReport('');
    }
  };

  const exportReport = async (report, action) => {
    try {
      setExportingAction(`${report.id}:${action}`);
      const exportPayload = await api.get(`/reports/${report.id}/export`);
      if (action === 'copy') {
        await copyToClipboard(exportPayload.markdown, 'Approved markdown copied');
      } else {
        downloadMarkdown(exportPayload.filename, exportPayload.markdown);
        toast.success('Markdown download started');
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setExportingAction('');
    }
  };

  return (
    <div className="stack" data-testid="reports-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Draft Output</div>
          <h1 className="page-title" data-testid="reports-page-title">Copy-ready reports stay isolated and readable</h1>
          <p className="page-subtitle" data-testid="reports-page-subtitle">Each report keeps its own markdown body and human-review gate so approved exports stay separate from draft review.</p>
        </div>
      </header>

      <section className="grid-2">
        {reports.map((report) => (
          <article key={report.id} className="panel" data-testid={`report-card-${report.id}`}>
            <div className="panel-header">
              <div>
                <div className="eyebrow" data-testid={`report-review-status-${report.id}`}>{report.review_status}</div>
                <h2 className="panel-title" data-testid={`report-title-${report.id}`}>{report.title}</h2>
              </div>
              <div className="button-row">
                {report.review_status !== 'approved' ? (
                  <Button onClick={() => approveReport(report)} disabled={approvingReport === report.id} variant="primary" data-testid={`report-approve-button-${report.id}`}>
                    {approvingReport === report.id ? 'Approving…' : 'Approve export'}
                  </Button>
                ) : null}
                <Button onClick={() => exportReport(report, 'copy')} disabled={!report.can_export || Boolean(exportingAction)} data-testid={`report-copy-approved-button-${report.id}`}>
                  {exportingAction === `${report.id}:copy` ? 'Copying…' : 'Copy approved markdown'}
                </Button>
                <Button onClick={() => exportReport(report, 'download')} disabled={!report.can_export || Boolean(exportingAction)} data-testid={`report-download-button-${report.id}`}>
                  {exportingAction === `${report.id}:download` ? 'Preparing…' : 'Download markdown'}
                </Button>
              </div>
            </div>
            <p className="panel-copy" data-testid={`report-summary-${report.id}`}>{report.executive_summary}</p>
            <p className="panel-copy" data-testid={`report-export-note-${report.id}`}>{report.can_export ? 'Approved markdown is ready for copy or download.' : 'Approval is still required before copy and download actions unlock.'}</p>
            <CopyBlock title={report.title} content={report.markdown} testId={`report-markdown-${report.id}`} copyable={false} />
          </article>
        ))}
      </section>
    </div>
  );
}
