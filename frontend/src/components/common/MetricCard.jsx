export const MetricCard = ({ eyebrow, value, label, note, testId }) => {
  return (
    <article className="metric-card" data-testid={testId}>
      <div className="eyebrow">{eyebrow}</div>
      <div className="metric-value">{value}</div>
      <div>{label}</div>
      <p className="metric-note">{note}</p>
    </article>
  );
};
