import { clsx } from 'clsx';

export const StatusBadge = ({ value, tone = 'default', testId }) => {
  const normalized = tone === 'severity' ? `badge--${String(value).toLowerCase()}` : '';
  const modeTone = value === 'exploratory' ? 'badge--passive' : value === 'consent_gated' ? 'badge--deep' : '';

  return (
    <span className={clsx('badge', normalized || modeTone)} data-testid={testId}>
      {String(value).replace('_', ' ')}
    </span>
  );
};
