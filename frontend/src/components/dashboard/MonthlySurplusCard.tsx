import React from 'react';
import SkeletonLoader from '../ui/SkeletonLoader';
import Button from '../ui/Button';

interface MonthlySurplusCardProps {
  value: string;
  change: string;
  loading?: boolean;
  empty?: boolean;
  error?: boolean;
}

export const MonthlySurplusCard: React.FC<MonthlySurplusCardProps> = ({
  value,
  change,
  loading = false,
  empty = false,
  error = false
}) => {
  if (loading) {
    return (
      <div className="card">
        <div className="label" style={{ width: '100%' }}>
          <SkeletonLoader width={120} height={16} className="mb-1" />
        </div>
        <div className="value" style={{ width: '60%' }}>
          <SkeletonLoader width={100} height={24} className="mb-1" />
        </div>
        <div className="change" style={{ width: '100%' }}>
          <SkeletonLoader width={80} height={16} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="label">Monthly investable surplus</div>
        <div className="value text-error">Error loading data</div>
        <div className="change">
          <span className="text-error">Unable to load</span>
        </div>
        <Button variant="secondary" size="sm" onClick={() => {
          // In a real app, this would trigger a refetch
          alert('Retry clicked');
        }}>
          Retry
        </Button>
      </div>
    );
  }

  if (empty) {
    return (
      <div className="card">
        <div className="label">Monthly investable surplus</div>
        <div className="value">—</div>
        <div className="change">—</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="label">Monthly investable surplus</div>
      <div className="value">{value}</div>
      <div className="change">{change}</div>
    </div>
  );
};