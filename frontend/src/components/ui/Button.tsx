import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  onClick,
  className = '',
  type = 'submit',
  ...buttonProps
}) => {
  const baseClasses = 'btn';
  const variantClasses =
    variant === 'primary'
      ? 'btn-primary'
      : variant === 'secondary'
      ? 'btn-secondary'
      : '';
  const sizeClasses =
    size === 'sm'
      ? 'btn-sm'
      : size === 'lg'
      ? 'btn-lg'
      : '';

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className}`}
      onClick={onClick}
      type={type}
      {...buttonProps}
    >
      {children}
    </button>
  );
};

export default Button;
