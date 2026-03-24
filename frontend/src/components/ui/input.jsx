import { clsx } from 'clsx';

export const Input = ({ className, ...props }) => {
  return <input className={clsx('input', className)} {...props} />;
};
