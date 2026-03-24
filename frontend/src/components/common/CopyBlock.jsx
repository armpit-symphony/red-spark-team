import { toast } from 'sonner';

import { Button } from '../ui/button';

export const CopyBlock = ({ title, content, testId }) => {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(content || '');
    toast.success(`${title} copied`);
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
