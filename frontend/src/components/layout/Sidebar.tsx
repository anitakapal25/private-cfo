import React from 'react';
import { NavItem } from '../dashboard/NavItem';
import { PrivacyNotice } from '../dashboard/PrivacyNotice';
import { Logo } from '../dashboard/Logo';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div>
        <Logo />
        <nav>
          <NavItem href="#" icon="layout-dashboard" label="Overview" active />
          <NavItem href="#" icon="target" label="Goals" />
          <NavItem href="#" icon="sliders-horizontal" label="Scenarios" />
          <NavItem href="#" icon="files" label="Documents" />
          <NavItem href="#" icon="list-checks" label="Action Plan" />
        </nav>
      </div>
      <div className="privacy">
        <PrivacyNotice />
      </div>
    </aside>
  );
};