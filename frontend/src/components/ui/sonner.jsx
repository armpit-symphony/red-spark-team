import { Toaster } from 'sonner';

export const AppToaster = () => (
  <Toaster
    position="top-right"
    theme="dark"
    richColors
    toastOptions={{
      className: 'panel',
      style: {
        borderRadius: 0,
        borderColor: '#27272A',
        background: '#111111',
        color: '#F4F4F5',
      },
    }}
  />
);
