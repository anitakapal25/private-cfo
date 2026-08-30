import React from 'react';
import Button from '../ui/Button';

interface ActionButtonProps {
  variant?: 'primary' | 'secondary';
  onClick?: () => void;
  className?: string;
  children: React.ReactNode;
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  variant = 'primary',
  onClick,
  className = '',
  children,
}) => {
  return <Button variant={variant} onClick={onClick} className={className}>
    {children}
  </Button>;
};