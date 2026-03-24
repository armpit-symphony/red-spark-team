import { clsx } from 'clsx';

export const Textarea = ({ className, ...props }) => {
  return <textarea className={clsx('textarea', className)} {...props} />;
};