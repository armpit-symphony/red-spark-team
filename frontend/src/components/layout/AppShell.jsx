import { ShieldChevron, Binoculars, FlagBanner, FlowArrow, BugBeetle, FileText, Sliders, TerminalWindow, LockKey } from '@phosphor-icons/react';
import { NavLink } from 'react-router-dom';

const links = [
  { to: '/overview', label: 'Overview', icon: ShieldChevron },
  { to: '/targets', label: 'Targets', icon: Binoculars },
  { to: '/policies', label: 'Policies', icon: LockKey },
  { to: '/audit-runs', label: 'Audit Runs', icon: FlowArrow },
  { to: '/findings', label: 'Findings', icon: BugBeetle },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Sliders },
  { to: '/audit-log', label: 'Audit Log', icon: TerminalWindow },
];

export const AppShell = ({ children }) => {
  return (
    <div className="app-shell">
      <div className="mobile-header" data-testid="mobile-app-header">
        <div className="eyebrow">Authorized Internal Use</div>
        <strong data-testid="mobile-app-title">Red Spark Team</strong>
      </div>
      <aside className="sidebar" data-testid="app-sidebar">
        <div className="sidebar__brand">
          <div className="eyebrow">Unified Audit Control Plane</div>
          <h1 className="sidebar__title" data-testid="sidebar-brand-title">Red Spark Team</h1>
          <p className="sidebar__copy" data-testid="sidebar-brand-copy">
            Single-admin internal workspace for governed red-team reviews, evidence capture, and report drafting.
          </p>
        </div>
        <nav className="nav-list" data-testid="sidebar-navigation">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
              data-testid={`nav-link-${label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <Icon size={18} weight="duotone" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__footer" data-testid="sidebar-footer-card">
          <div className="eyebrow">Operator Mode</div>
          <div className="button-row" style={{ marginTop: 12 }}>
            <span className="badge badge--passive" data-testid="operator-passive-badge">exploratory</span>
            <span className="badge badge--deep" data-testid="operator-deep-badge">consent gated</span>
          </div>
          <p className="sidebar__copy" style={{ marginTop: 12 }} data-testid="operator-mode-copy">
            Deep mode remains visually isolated and token-gated before an audit run can begin.
          </p>
          <div className="button-row" style={{ marginTop: 12 }}>
            <FlagBanner size={18} weight="duotone" />
            <span className="muted" data-testid="single-admin-mode-copy">Single admin mode</span>
          </div>
        </div>
      </aside>
      <main className="content">
        <div className="content__inner">{children}</div>
      </main>
    </div>
  );
};