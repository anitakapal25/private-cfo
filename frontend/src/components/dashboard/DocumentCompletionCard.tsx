import React from 'react';
import Icon from '@/components/ui/Icon';

interface DocumentCompletionCardProps {
  documentName: string;
  actionText: string;
  onUpload: () => void;
  steps: Array<{
    label: string;
    iconName: string;
    completed: boolean;
  }>;
}

export const DocumentCompletionCard: React.FC<DocumentCompletionCardProps> = ({
  documentName,
  actionText,
  onUpload,
  steps
}) => {
  return (
    <div className="doc-card">
      <h3>Complete Your Financial Picture</h3>
      <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
        <Icon name="upload-cloud" size={20} />
        <span>Upload your latest {documentName}</span>
      </div>
      <div className="upload-area" onClick={onUpload} role="button" tabIndex={0}>
        <p>{actionText}</p>
      </div>
      <ul style={{ listStyle: 'none', paddingLeft: 0, fontSize: '.875rem', color: 'var(--color-text-secondary)', marginTop: '.5rem' }}>
        {steps.map((step, index) => (
          <li key={index} className="upload-step" style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <Icon name={step.iconName} size={16} />
            <span>{step.label}</span>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: '.75rem', color: 'var(--color-text-secondary)', marginTop: '.5rem' }}>
        Nothing is added until you confirm it.
      </p>
    </div>
  );
};