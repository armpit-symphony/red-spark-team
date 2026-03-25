import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';

import { CopyBlock } from '../components/common/CopyBlock';
import { StatusBadge } from '../components/common/StatusBadge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs } from '../components/ui/tabs';
import { Textarea } from '../components/ui/textarea';
import { copyToClipboard } from '../lib/clipboard';
import { api } from '../lib/api';

const tabOptions = [
  { label: 'Tasks', value: 'tasks' },
  { label: 'Findings', value: 'findings' },
  { label: 'Evidence', value: 'evidence' },
  { label: 'Report', value: 'report' },
];

const initialImportDraft = {
  source_name: 'Scanner Import',
  import_format: 'text',
  content: '',
};

const syncSectionDrafts = (sections) => sections.reduce((accumulator, section) => ({
  ...accumulator,
  [section.section_key]: { title: section.title, content: section.content, format: section.format },
}), {});

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

export default function RunDetailPage() {
  const { runId } = useParams();
  const [activeTab, setActiveTab] = useState('tasks');
  const [bundle, setBundle] = useState({ run: null, tasks: [], findings: [], sections: [], report: null });
  const [providers, setProviders] = useState([]);
  const [analysisConfig, setAnalysisConfig] = useState({ provider: 'openai', model: 'gpt-5.2', analysis_type: 'report_draft', focus: '', routing_policy_id: 'direct' });
  const [sectionDrafts, setSectionDrafts] = useState({});
  const [openRouterCatalog, setOpenRouterCatalog] = useState({ models: [], model_count: 0, source: '', refresh_status: '' });
  const [routingState, setRoutingState] = useState({ default_policy_id: 'direct', policies: [] });
  const [routingTelemetry, setRoutingTelemetry] = useState(null);
  const [routingTelemetryLoading, setRoutingTelemetryLoading] = useState(false);
  const [importDraft, setImportDraft] = useState(initialImportDraft);
  const [importSummary, setImportSummary] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [exportingAction, setExportingAction] = useState('');

  const loadBundle = useCallback(async () => {
    const [runData, providerData, catalogData, routingData] = await Promise.all([api.get(`/runs/${runId}`), api.get('/providers'), api.get('/model-catalog?provider=openrouter'), api.get('/routing-policies')]);
    setBundle(runData);
    setProviders(providerData.filter((provider) => provider.enabled));
    setOpenRouterCatalog(catalogData);
    setRoutingState(routingData);
    const firstProvider = providerData.find((provider) => provider.enabled);
    if (firstProvider) {
      setAnalysisConfig((current) => ({ ...current, provider: firstProvider.provider, model: firstProvider.model, routing_policy_id: routingData.default_policy_id || current.routing_policy_id }));
    }
    setSectionDrafts(syncSectionDrafts(runData.sections));
  }, [runId]);

  useEffect(() => {
    loadBundle().catch((error) => toast.error(error.message));
  }, [loadBundle]);

  const run = bundle.run;
  const reportMarkdown = useMemo(() => bundle.report?.markdown || sectionDrafts['report-draft']?.content || 'No report draft yet.', [bundle.report, sectionDrafts]);
  const selectedRoutingPolicy = useMemo(() => routingState.policies.find((policy) => policy.id === analysisConfig.routing_policy_id) || null, [routingState, analysisConfig.routing_policy_id]);

  const loadRoutingTelemetry = useCallback(async (policyId) => {
    if (!policyId || policyId === 'direct') {
      setRoutingTelemetry(null);
      return;
    }

    try {
      setRoutingTelemetryLoading(true);
      const telemetry = await api.get(`/routing-policies/${policyId}/telemetry?window=25`);
      setRoutingTelemetry(telemetry);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setRoutingTelemetryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoutingTelemetry(analysisConfig.routing_policy_id);
  }, [analysisConfig.routing_policy_id, loadRoutingTelemetry]);

  const saveSection = async (sectionKey) => {
    try {
      const draft = sectionDrafts[sectionKey];
      const updated = await api.post(`/runs/${runId}/sections`, { section_key: sectionKey, title: draft.title, content: draft.content, format: draft.format || 'text' });
      setBundle(updated);
      toast.success(`${draft.title} saved`);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const runAnalysis = async () => {
    try {
      const updated = await api.post(`/runs/${runId}/analysis`, analysisConfig);
      setBundle(updated);
      setSectionDrafts(syncSectionDrafts(updated.sections));
      await loadRoutingTelemetry(analysisConfig.routing_policy_id);
      toast.success('Analysis complete');
    } catch (error) {
      toast.error(error.message);
    }
  };

  const importScannerOutput = async () => {
    try {
      setIsImporting(true);
      const result = await api.post(`/runs/${runId}/scanner-import`, importDraft);
      setBundle(result.bundle);
      setSectionDrafts(syncSectionDrafts(result.bundle.sections));
      setImportSummary(result.summary);
      setImportDraft((current) => ({ ...current, content: '' }));
      toast.success(`Imported ${result.summary.imported_count} finding(s)`);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsImporting(false);
    }
  };

  const approveReport = async () => {
    if (!bundle.report) {
      return;
    }

    try {
      setIsApproving(true);
      const approved = await api.post(`/reports/${bundle.report.id}/approve`, {});
      setBundle((current) => ({ ...current, report: approved }));
      toast.success('Report approved for export');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsApproving(false);
    }
  };

  const exportReport = async (action) => {
    if (!bundle.report) {
      return;
    }

    try {
      setExportingAction(action);
      const exportPayload = await api.get(`/reports/${bundle.report.id}/export`);
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

  if (!run) {
    return <div className="empty-state" data-testid="run-detail-loading">Loading run workspace...</div>;
  }

  return (
    <div className="stack" data-testid="run-detail-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Run Workspace</div>
          <h1 className="page-title" data-testid="run-detail-title">{run.target_name}</h1>
          <p className="page-subtitle" data-testid="run-detail-subtitle">{run.objective}</p>
        </div>
        <div className="stack-sm">
          <div className="button-row">
            <StatusBadge value={run.mode} testId="run-detail-mode-badge" />
            <span className="badge" data-testid="run-detail-status-badge">{run.status}</span>
          </div>
          <div className="mono muted" data-testid="run-detail-target-locator">{run.target_locator}</div>
        </div>
      </header>

      {run.mode === 'consent_gated' ? <div className="mode-alert" data-testid="run-detail-deep-banner">Consent-gated mode is active for this run. Keep evidence handling tight and export review enabled.</div> : null}

      <section className="panel" data-testid="run-detail-analysis-panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">LLM-Assisted Analysis</div>
            <h2 className="panel-title">Draft summaries, remediation, and report output</h2>
          </div>
          <Button onClick={runAnalysis} variant={analysisConfig.analysis_type === 'report_draft' ? 'primary' : 'ghost'} data-testid="run-analysis-submit-button">Run analysis</Button>
        </div>
        <div className="field-grid" style={{ marginTop: 16 }}>
          <div className="field"><label className="field-label">Routing policy</label><select className="select" value={analysisConfig.routing_policy_id} onChange={(e) => setAnalysisConfig({ ...analysisConfig, routing_policy_id: e.target.value })} data-testid="run-analysis-routing-policy-select"><option value="direct">Direct provider selection</option>{routingState.policies.map((policy) => <option key={policy.id} value={policy.id}>{policy.label}</option>)}</select></div>
          {analysisConfig.routing_policy_id === 'direct' ? <div className="field"><label className="field-label">Provider</label><select className="select" value={analysisConfig.provider} onChange={(e) => { const selected = providers.find((provider) => provider.provider === e.target.value); setAnalysisConfig({ ...analysisConfig, provider: e.target.value, model: selected?.model || analysisConfig.model }); }} data-testid="run-analysis-provider-select">{providers.map((provider) => <option key={provider.provider} value={provider.provider}>{provider.label}</option>)}</select></div> : <div className="field"><label className="field-label">Preferred route</label><div className="panel-copy" data-testid="run-analysis-primary-route">{routingTelemetry?.preferred_route ? `${routingTelemetry.preferred_route.provider} · ${routingTelemetry.preferred_route.model}` : selectedRoutingPolicy ? `${selectedRoutingPolicy.primary.provider} · ${selectedRoutingPolicy.primary.model}` : 'No routing policy selected'}</div></div>}
          {analysisConfig.routing_policy_id === 'direct' ? <div className="field"><label className="field-label">Model</label>{analysisConfig.provider === 'openrouter' && openRouterCatalog.models.length ? <select className="select" value={analysisConfig.model} onChange={(e) => setAnalysisConfig({ ...analysisConfig, model: e.target.value })} data-testid="run-analysis-model-select">{openRouterCatalog.models.some((model) => model.model_id === analysisConfig.model) ? null : <option value={analysisConfig.model}>{analysisConfig.model}</option>}{openRouterCatalog.models.map((model) => <option key={model.model_id} value={model.model_id}>{model.name}</option>)}</select> : <Input value={analysisConfig.model} onChange={(e) => setAnalysisConfig({ ...analysisConfig, model: e.target.value })} data-testid="run-analysis-model-input" />}{analysisConfig.provider === 'openrouter' ? <div className="muted" style={{ marginTop: 8 }} data-testid="run-analysis-openrouter-catalog-meta">{openRouterCatalog.model_count || 0} catalog models · {openRouterCatalog.source || 'unknown source'}</div> : null}</div> : <div className="field"><label className="field-label">Backup route</label><div className="panel-copy" data-testid="run-analysis-fallback-route">{routingTelemetry?.backup_route ? `${routingTelemetry.backup_route.provider} · ${routingTelemetry.backup_route.model}` : selectedRoutingPolicy ? `${selectedRoutingPolicy.fallback.provider} · ${selectedRoutingPolicy.fallback.model}` : 'No fallback route configured'}</div><div className="muted" style={{ marginTop: 8 }} data-testid="run-analysis-routing-note">One fallback only. If both routes fail, the analysis error explains why.</div></div>}
          <div className="field"><label className="field-label">Output type</label><select className="select" value={analysisConfig.analysis_type} onChange={(e) => setAnalysisConfig({ ...analysisConfig, analysis_type: e.target.value })} data-testid="run-analysis-type-select"><option value="report_draft">Report draft</option><option value="finding_summary">Finding summary</option><option value="remediation_plan">Remediation plan</option></select></div>
          <div className="field"><label className="field-label">Focus</label><Input value={analysisConfig.focus} onChange={(e) => setAnalysisConfig({ ...analysisConfig, focus: e.target.value })} data-testid="run-analysis-focus-input" /></div>
        </div>
        {analysisConfig.routing_policy_id !== 'direct' ? <div className="stack" style={{ marginTop: 16 }} data-testid="run-analysis-routing-telemetry-panel"><div className="panel-header"><div><div className="eyebrow">Routing telemetry</div><h3 className="panel-title">Last 25 routed analyses for this policy</h3></div>{routingTelemetryLoading ? <span className="badge" data-testid="run-analysis-routing-telemetry-loading">loading</span> : null}</div>{routingTelemetry ? <><div className="grid-2"><article className="panel" data-testid="run-analysis-routing-preferred-card"><div className="eyebrow">Preferred score</div><div className="panel-title">{routingTelemetry.preferred_route.provider} · {routingTelemetry.preferred_route.model}</div><div className="stack-sm" style={{ marginTop: 12 }}><div className="muted" data-testid="run-analysis-routing-preferred-success">Success rate: {Math.round((routingTelemetry.preferred_route.success_rate || 0) * 100)}%</div><div className="muted" data-testid="run-analysis-routing-preferred-latency">Avg latency: {routingTelemetry.preferred_route.avg_latency_ms} ms</div><div className="muted" data-testid="run-analysis-routing-preferred-cost">Cost score: {routingTelemetry.preferred_route.cost_units}</div></div></article><article className="panel" data-testid="run-analysis-routing-backup-card"><div className="eyebrow">Backup score</div><div className="panel-title">{routingTelemetry.backup_route.provider} · {routingTelemetry.backup_route.model}</div><div className="stack-sm" style={{ marginTop: 12 }}><div className="muted" data-testid="run-analysis-routing-backup-success">Success rate: {Math.round((routingTelemetry.backup_route.success_rate || 0) * 100)}%</div><div className="muted" data-testid="run-analysis-routing-backup-latency">Avg latency: {routingTelemetry.backup_route.avg_latency_ms} ms</div><div className="muted" data-testid="run-analysis-routing-backup-cost">Cost score: {routingTelemetry.backup_route.cost_units}</div></div></article></div><div className="stack-sm" style={{ marginTop: 16 }}>{routingTelemetry.recent_traces.slice(0, 6).map((trace) => <div key={trace.id} className="panel" data-testid={`run-analysis-routing-trace-${trace.id}`}><div className="panel-header"><div className="panel-title">{trace.selected_provider} · {trace.selected_model}</div><span className="badge" data-testid={`run-analysis-routing-trace-status-${trace.id}`}>{trace.success ? 'success' : 'failed'}</span></div><div className="muted" data-testid={`run-analysis-routing-trace-meta-${trace.id}`}>{trace.latency_ms} ms · {trace.used_as_fallback ? 'fallback attempt' : 'preferred attempt'}</div>{trace.error_message ? <div className="muted" data-testid={`run-analysis-routing-trace-error-${trace.id}`}>{trace.error_message}</div> : null}</div>)}</div></> : <div className="muted" data-testid="run-analysis-routing-telemetry-empty">No routing telemetry yet for this policy.</div>}</div> : null}
      </section>

      <Tabs tabs={tabOptions} activeTab={activeTab} onChange={setActiveTab}>
        {activeTab === 'tasks' ? (
          <section className="timeline" data-testid="run-detail-tasks-view">
            {bundle.tasks.map((task) => (
              <article key={task.id} className="timeline-item" data-testid={`run-task-${task.id}`}>
                <div className="panel-header"><h2 className="panel-title">{task.title}</h2><span className="badge" data-testid={`run-task-status-${task.id}`}>{task.status}</span></div>
                <div className="eyebrow">{task.task_type}</div>
                <p className="panel-copy" data-testid={`run-task-output-${task.id}`}>{task.output}</p>
              </article>
            ))}
          </section>
        ) : null}

        {activeTab === 'findings' ? (
          <section className="stack" data-testid="run-detail-findings-view">
            <article className="form-shell" data-testid="scanner-import-panel">
              <div className="panel-header">
                <div>
                  <div className="eyebrow">Scanner Import</div>
                  <h2 className="panel-title">Import text or JSON into normalized findings</h2>
                  <p className="panel-copy" data-testid="scanner-import-panel-copy">Paste scanner output here. Items without a title or severity are skipped automatically.</p>
                </div>
                <Button onClick={importScannerOutput} disabled={isImporting} variant="primary" data-testid="scanner-import-submit-button">
                  {isImporting ? 'Importing…' : 'Import findings'}
                </Button>
              </div>
              <div className="field-grid" style={{ marginTop: 16 }}>
                <div className="field"><label className="field-label">Source name</label><Input value={importDraft.source_name} onChange={(event) => setImportDraft({ ...importDraft, source_name: event.target.value })} data-testid="scanner-import-source-input" /></div>
                <div className="field"><label className="field-label">Format</label><select className="select" value={importDraft.import_format} onChange={(event) => setImportDraft({ ...importDraft, import_format: event.target.value })} data-testid="scanner-import-format-select"><option value="text">Text</option><option value="json">JSON</option></select></div>
              </div>
              <div className="field-stack">
                <label className="field-label">Scanner output</label>
                <Textarea value={importDraft.content} onChange={(event) => setImportDraft({ ...importDraft, content: event.target.value })} data-testid="scanner-import-content-textarea" />
              </div>
              {importSummary ? (
                <div className="import-summary" data-testid="scanner-import-summary">
                  <div className="button-row">
                    <span className="badge" data-testid="scanner-import-imported-count">Imported {importSummary.imported_count}</span>
                    <span className="badge" data-testid="scanner-import-skipped-count">Skipped {importSummary.skipped_count}</span>
                    <span className="badge" data-testid="scanner-import-detected-count">Detected {importSummary.detected_count}</span>
                  </div>
                  {importSummary.skipped_items?.length ? (
                    <div className="stack-sm" style={{ marginTop: 12 }}>
                      {importSummary.skipped_items.map((item, index) => <div key={`${item}-${index}`} className="muted" data-testid={`scanner-import-skipped-item-${index}`}>{item}</div>)}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </article>

            <section className="grid-2" data-testid="run-detail-findings-grid">
              {bundle.findings.length ? bundle.findings.map((finding) => (
                <article key={finding.id} className="panel" data-testid={`run-finding-${finding.id}`}>
                  <div className="panel-header"><h2 className="panel-title">{finding.title}</h2><StatusBadge value={finding.severity} tone="severity" testId={`run-finding-severity-${finding.id}`} /></div>
                  <div className="button-row" style={{ marginTop: 12 }}>
                    <span className="badge" data-testid={`run-finding-status-${finding.id}`}>{finding.status}</span>
                    {finding.source_name ? <span className="badge" data-testid={`run-finding-source-${finding.id}`}>{finding.source_name} · {finding.import_format || 'manual'}</span> : null}
                  </div>
                  <p className="panel-copy" data-testid={`run-finding-evidence-${finding.id}`}>{finding.evidence}</p>
                  <div className="eyebrow">Remediation</div>
                  <p className="panel-copy" data-testid={`run-finding-remediation-${finding.id}`}>{finding.remediation}</p>
                </article>
              )) : <div className="empty-state" data-testid="run-detail-findings-empty-state">No findings have been promoted for this run yet. Save evidence sections, import scanner results, or request an LLM summary to prepare the next review pass.</div>}
            </section>
          </section>
        ) : null}

        {activeTab === 'evidence' ? (
          <section className="grid-2" data-testid="run-detail-evidence-view">
            {bundle.sections.map((section) => (
              <article key={section.section_key} className="form-shell" data-testid={`run-section-${section.section_key}`}>
                <div className="panel-header">
                  <div>
                    <div className="eyebrow">Section</div>
                    <h2 className="panel-title">{section.title}</h2>
                  </div>
                  <div className="button-row">
                    <Button onClick={() => saveSection(section.section_key)} variant="primary" data-testid={`run-section-save-${section.section_key}`}>Save</Button>
                    <Button onClick={() => copyToClipboard(sectionDrafts[section.section_key]?.content || '', `${section.title} copied`)} data-testid={`run-section-copy-${section.section_key}`}>Copy</Button>
                  </div>
                </div>
                <Textarea
                  value={sectionDrafts[section.section_key]?.content || ''}
                  onChange={(event) => setSectionDrafts({ ...sectionDrafts, [section.section_key]: { ...sectionDrafts[section.section_key], title: section.title, format: section.format, content: event.target.value } })}
                  data-testid={`run-section-textarea-${section.section_key}`}
                />
              </article>
            ))}
          </section>
        ) : null}

        {activeTab === 'report' ? (
          <section className="stack" data-testid="run-detail-report-view">
            <article className="panel" data-testid="run-detail-report-panel">
              <div className="panel-header">
                <div>
                  <div className="eyebrow">Draft markdown</div>
                  <h2 className="panel-title">Report output</h2>
                  <p className="panel-copy" data-testid="run-detail-report-export-note">Human approval is required before markdown can be copied or downloaded.</p>
                </div>
                {bundle.report ? (
                  <div className="button-row">
                    <span className={`badge ${bundle.report.review_status === 'approved' ? 'badge--approved' : 'badge--review'}`} data-testid="run-detail-report-review-status">{bundle.report.review_status.replace('_', ' ')}</span>
                    {bundle.report.review_status !== 'approved' ? <Button onClick={approveReport} disabled={isApproving} variant="primary" data-testid="run-detail-report-approve-button">{isApproving ? 'Approving…' : 'Approve export'}</Button> : null}
                    <Button onClick={() => exportReport('copy')} disabled={!bundle.report.can_export || Boolean(exportingAction)} data-testid="run-detail-report-copy-approved-button">{exportingAction === 'copy' ? 'Copying…' : 'Copy approved markdown'}</Button>
                    <Button onClick={() => exportReport('download')} disabled={!bundle.report.can_export || Boolean(exportingAction)} data-testid="run-detail-report-download-button">{exportingAction === 'download' ? 'Preparing…' : 'Download markdown'}</Button>
                  </div>
                ) : null}
              </div>
              <CopyBlock title="Report Draft" content={reportMarkdown} testId="run-detail-report-markdown" copyable={false} />
            </article>
          </section>
        ) : null}
      </Tabs>
    </div>
  );
}