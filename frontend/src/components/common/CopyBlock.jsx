import { toast } from 'sonner';

import { Button } from '../ui/button';
import { copyToClipboard } from '../../lib/clipboard';

export const CopyBlock = ({ title, content, testId }) => {
  const handleCopy = async () => {
    await copyToClipboard(content || '', `${title} copied`);
  };

  return (
    <div className="code-block" data-testid={testId}>
      <Button className="copy-button" variant="ghost" onClick={handleCopy} data-testid={`${testId}-copy-button`}>
        Copy
      </Button>
      {content}
    </div>
  );
};
