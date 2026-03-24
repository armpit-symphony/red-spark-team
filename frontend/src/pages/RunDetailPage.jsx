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

export default function RunDetailPage() {
  const { runId } = useParams();
  const [activeTab, setActiveTab] = useState('tasks');
  const [bundle, setBundle] = useState({ run: null, tasks: [], findings: [], sections: [], report: null });
  const [providers, setProviders] = useState([]);
  const [analysisConfig, setAnalysisConfig] = useState({ provider: 'openai', model: 'gpt-5.2', analysis_type: 'report_draft', focus: '' });
  const [sectionDrafts, setSectionDrafts] = useState({});

  const loadBundle = useCallback(async () => {
    const [runData, providerData] = await Promise.all([api.get(`/runs/${runId}`), api.get('/providers')]);
    setBundle(runData);
    setProviders(providerData.filter((provider) => provider.enabled));
    const firstProvider = providerData.find((provider) => provider.enabled);
    if (firstProvider) {
      setAnalysisConfig((current) => ({ ...current, provider: firstProvider.provider, model: firstProvider.model }));
    }
    setSectionDrafts(
      runData.sections.reduce((accumulator, section) => ({
        ...accumulator,
        [section.section_key]: { title: section.title, content: section.content, format: section.format },
      }), {})
    );
  }, [runId]);

  useEffect(() => {
    loadBundle().catch((error) => toast.error(error.message));
  }, [loadBundle]);

  const run = bundle.run;
  const reportMarkdown = useMemo(() => bundle.report?.markdown || sectionDrafts['report-draft']?.content || 'No report draft yet.', [bundle.report, sectionDrafts]);

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
      setSectionDrafts(
        updated.sections.reduce((accumulator, section) => ({
          ...accumulator,
          [section.section_key]: { title: section.title, content: section.content, format: section.format },
        }), {})
      );
      toast.success('Analysis complete');
    } catch (error) {
      toast.error(error.message);
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
          <div className="field"><label className="field-label">Provider</label><select className="select" value={analysisConfig.provider} onChange={(e) => { const selected = providers.find((provider) => provider.provider === e.target.value); setAnalysisConfig({ ...analysisConfig, provider: e.target.value, model: selected?.model || analysisConfig.model }); }} data-testid="run-analysis-provider-select">{providers.map((provider) => <option key={provider.provider} value={provider.provider}>{provider.label}</option>)}</select></div>
          <div className="field"><label className="field-label">Model</label><Input value={analysisConfig.model} onChange={(e) => setAnalysisConfig({ ...analysisConfig, model: e.target.value })} data-testid="run-analysis-model-input" /></div>
          <div className="field"><label className="field-label">Output type</label><select className="select" value={analysisConfig.analysis_type} onChange={(e) => setAnalysisConfig({ ...analysisConfig, analysis_type: e.target.value })} data-testid="run-analysis-type-select"><option value="report_draft">Report draft</option><option value="finding_summary">Finding summary</option><option value="remediation_plan">Remediation plan</option></select></div>
          <div className="field"><label className="field-label">Focus</label><Input value={analysisConfig.focus} onChange={(e) => setAnalysisConfig({ ...analysisConfig, focus: e.target.value })} data-testid="run-analysis-focus-input" /></div>
        </div>
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
          <section className="grid-2" data-testid="run-detail-findings-view">
            {bundle.findings.length ? bundle.findings.map((finding) => (
              <article key={finding.id} className="panel" data-testid={`run-finding-${finding.id}`}>
                <div className="panel-header"><h2 className="panel-title">{finding.title}</h2><StatusBadge value={finding.severity} tone="severity" testId={`run-finding-severity-${finding.id}`} /></div>
                <p className="panel-copy" data-testid={`run-finding-evidence-${finding.id}`}>{finding.evidence}</p>
                <div className="eyebrow">Remediation</div>
                <p className="panel-copy" data-testid={`run-finding-remediation-${finding.id}`}>{finding.remediation}</p>
              </article>
            )) : <div className="empty-state" data-testid="run-detail-findings-empty-state">No findings have been promoted for this run yet. Save evidence sections or request an LLM summary to prepare the next review pass.</div>}
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
              <div className="panel-header"><div><div className="eyebrow">Draft markdown</div><h2 className="panel-title">Report output</h2></div></div>
              <CopyBlock title="Report Draft" content={reportMarkdown} testId="run-detail-report-markdown" />
            </article>
          </section>
        ) : null}
      </Tabs>
    </div>
  );
}