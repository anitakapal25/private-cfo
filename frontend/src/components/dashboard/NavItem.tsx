import React from 'react';
import Icon from '@/components/ui/Icon';

interface NavItemProps {
  href: string;
  icon: string; // Lucide icon name
  label: string;
  active?: boolean;
}

export const NavItem: React.FC<NavItemProps> = ({
  href,
  icon,
  label,
  active = false
}) => {
  return (
    <a
      href={href}
      className={`${active ? 'active' : ''}`}
    >
      <Icon name={icon} size={16} />
      <span>{label}</span>
    </a>
  );
};