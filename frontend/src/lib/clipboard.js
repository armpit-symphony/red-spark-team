import { toast } from 'sonner';

export async function copyToClipboard(value, successMessage = 'Copied to clipboard') {
  try {
    await navigator.clipboard.writeText(value || '');
    toast.success(successMessage);
  } catch (error) {
    toast.error('Clipboard access was denied. You can still select and copy the text manually.');
  }
}
