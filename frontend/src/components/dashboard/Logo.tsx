import React from 'react';
import Icon from '@/components/ui/Icon';

export const Logo: React.FC = () => {
  return (
    <div className="logo">
      <Icon name="layout-dashboard" size={20} />
      <span>ArthaOS</span>
    </div>
  );
};