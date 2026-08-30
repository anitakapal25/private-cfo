import React from 'react';
import { ActionButton } from '../dashboard/ActionButton';
import { NotificationIcon } from '../dashboard/NotificationIcon';
import { Avatar } from '../dashboard/Avatar';

export const Header: React.FC = () => {
  return (
    <header className="top-header">
      <h1>Financial Freedom Overview</h1>
      <div className="actions">
        <ActionButton variant="secondary">Upload Statement</ActionButton>
        <ActionButton variant="primary">Ask Artha</ActionButton>
        <NotificationIcon />
        <Avatar />
      </div>
    </header>
  );
};