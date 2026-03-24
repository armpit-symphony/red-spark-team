import { clsx } from 'clsx';

export const Button = ({ className, variant = 'default', type = 'button', ...props }) => {
  const variantClass = {
    default: '',
    primary: 'button--primary',
    danger: 'button--danger',
    ghost: 'button--ghost',
  }[variant];

  return <button type={type} className={clsx('button', variantClass, className)} {...props} />;
};
