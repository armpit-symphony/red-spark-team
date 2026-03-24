export const Tabs = ({ tabs, activeTab, onChange, children }) => {
  return (
    <div className="tabs">
      <div className="tab-list" data-testid="run-detail-tab-list">
        <div>
          {tabs.map((tab) => (
            <button
              key={tab.value}
              type="button"
              className={`tab-button ${activeTab === tab.value ? 'tab-button--active' : ''}`}
              onClick={() => onChange(tab.value)}
              data-testid={`run-detail-tab-${tab.value}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div data-testid={`run-detail-panel-${activeTab}`}>{children}</div>
    </div>
  );
};
