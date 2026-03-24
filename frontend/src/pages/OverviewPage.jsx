import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { MetricCard } from '../components/common/MetricCard';
import { api } from '../lib/api';

const emptyOverview = {
  stats: { targets: 0, runs: 0, findings: 0, reports: 0 },
  severity_chart: [],
  run_volume_chart: [],
  recent_logs: [],
};

export default function OverviewPage() {
  const [overview, setOverview] = useState(emptyOverview);
  const [chartsReady, setChartsReady] = useState(false);

  useEffect(() => {
    api.get('/overview').then(setOverview).catch(console.error);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setChartsReady(true), 150);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="stack" data-testid="overview-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Authorized Internal Audit Platform</div>
          <h1 className="page-title" data-testid="overview-page-title">Unified control plane for governed review runs</h1>
          <p className="page-subtitle" data-testid="overview-page-subtitle">
            Monitor targets, isolate evidence sections, and keep draft reports readable enough to copy directly into downstream handoff workflows.
          </p>
        </div>
      </header>

      <section className="grid-4">
        <MetricCard eyebrow="Targets" value={overview.stats.targets} label="Scoped assets" note="Explicit allowlists only" testId="metric-targets" />
        <MetricCard eyebrow="Audit Runs" value={overview.stats.runs} label="Tracked workflows" note="Planner, evidence, reporting" testId="metric-runs" />
        <MetricCard eyebrow="Findings" value={overview.stats.findings} label="Normalized issues" note="Stored in canonical schema" testId="metric-findings" />
        <MetricCard eyebrow="Reports" value={overview.stats.reports} label="Draft packs" note="Human review stays required" testId="metric-reports" />
      </section>

      <section className="grid-2">
        <article className="panel" data-testid="severity-chart-panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Finding Mix</div>
              <h2 className="panel-title">Severity distribution</h2>
            </div>
          </div>
          <div className="chart-shell" data-testid="severity-chart-shell">
            {chartsReady ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={300}>
                <BarChart data={overview.severity_chart}>
                  <CartesianGrid stroke="#27272A" vertical={false} />
                  <XAxis dataKey="name" stroke="#A1A1AA" tickLine={false} axisLine={false} />
                  <YAxis stroke="#A1A1AA" tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: '#111111', border: '1px solid #27272A' }} />
                  <Bar dataKey="value" fill="#4F46E5" radius={0} />
                </BarChart>
              </ResponsiveContainer>
            ) : null}
          </div>
        </article>

        <article className="panel" data-testid="run-volume-chart-panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">Audit Activity</div>
              <h2 className="panel-title">Run volume over time</h2>
            </div>
          </div>
          <div className="chart-shell" data-testid="run-volume-chart-shell">
            {chartsReady ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={300}>
                <LineChart data={overview.run_volume_chart}>
                  <CartesianGrid stroke="#27272A" vertical={false} />
                  <XAxis dataKey="day" stroke="#A1A1AA" tickLine={false} axisLine={false} />
                  <YAxis stroke="#A1A1AA" tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: '#111111', border: '1px solid #27272A' }} />
                  <Line type="monotone" dataKey="runs" stroke="#F97316" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : null}
          </div>
        </article>
      </section>

      <section className="panel" data-testid="recent-log-panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Recent Activity</div>
            <h2 className="panel-title">Audit log highlights</h2>
          </div>
        </div>
        <div className="timeline" data-testid="recent-log-timeline">
          {overview.recent_logs.map((item) => (
            <div key={item.id} className="timeline-item" data-testid={`recent-log-item-${item.id}`}>
              <div className="timeline-item__time">{new Date(item.created_at).toLocaleString()}</div>
              <div style={{ marginTop: 10 }}>{item.action}</div>
              <div className="muted" style={{ marginTop: 8 }}>{item.details}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
