import React from 'react';
import Icon from '@/components/ui/Icon';

interface DataConfidencePanelProps {
  confidenceScore: number;
  itemsReviewed: string;
  dataItems: Array<{
    name: string;
    source: string;
    status: 'verified' | 'update' | 'review';
  }>;
  assumptionsLinkText?: string;
}

export const DataConfidencePanel: React.FC<DataConfidencePanelProps> = ({
  confidenceScore,
  itemsReviewed,
  dataItems,
  assumptionsLinkText = 'View Assumptions'
}) => {
  return (
    <div className="panel">
      <div className="confidence-header">
        <h3>Data Confidence</h3>
        <div className="score" style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--color-primary-action)' }}>
          {confidenceScore}%
        </div>
      </div>
      <p style={{ fontSize: '.875rem', color: 'var(--color-text-secondary)' }}>
        {itemsReviewed} need review
      </p>
      <div className="confidence-list">
        {dataItems.map((item, index) => (
          <div key={index} className="conf-item">
            <div>
              <strong>{item.name}</strong>
              <div className="source">{item.source}</div>
            </div>
            <div className={`status ${item.status}`}>
              <Icon
                name={item.status === 'verified' ? 'shield-check' :
                       item.status === 'update' ? 'clock' : 'circle-help'}
                size={16}
              />
              <span>{item.status === 'verified' ? 'Verified' :
                       item.status === 'update' ? 'Update due' : 'Review'}</span>
            </div>
          </div>
        ))}
      </div>
      <p style={{ marginTop: '.75rem', fontSize: '.875rem', color: 'var(--color-text-secondary)' }}>
        Your financial‑freedom estimate uses 14 verified inputs, 2 estimates, and 1 outdated value.
      </p>
      <a href="#" style={{ color: 'var(--color-primary-action)', fontWeight: 500 }}>
        {assumptionsLinkText}
      </a>
    </div>
  );
};