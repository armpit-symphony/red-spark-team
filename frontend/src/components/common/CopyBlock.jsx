import { Button } from '../ui/button';
import { copyToClipboard } from '../../lib/clipboard';

export const CopyBlock = ({ title, content, testId, copyable = true, copyLabel = 'Copy' }) => {
  const handleCopy = async () => {
    await copyToClipboard(content || '', `${title} copied`);
  };

  return (
    <div className="code-block" data-testid={testId}>
      {copyable ? (
        <Button className="copy-button" variant="ghost" onClick={handleCopy} data-testid={`${testId}-copy-button`}>
          {copyLabel}
        </Button>
      ) : null}
      {content}
    </div>
  );
};
