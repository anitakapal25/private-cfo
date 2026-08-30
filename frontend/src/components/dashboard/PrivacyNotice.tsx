import React from 'react';

export const PrivacyNotice: React.FC = () => {
  return (
    <div className="privacy">
      {/* Using Lucide icon placeholder */}
      <span aria-hidden="true">🔒</span>
      <span>Your financial data stays private and is never exposed to public research tools.</span>
    </div>
  );
};