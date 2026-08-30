import React from 'react';
import SkeletonLoader from '../ui/SkeletonLoader';
import Button from '../ui/Button';

interface NetWorthCardProps {
  value: string;
  change: string;
  isIncrease?: boolean;
  loading?: boolean;
  empty?: boolean;
  error?: boolean;
}

export const NetWorthCard: React.FC<NetWorthCardProps> = ({
  value,
  change,
  isIncrease = true,
  loading = false,
  empty = false,
  error = false
}) => {
  if (loading) {
    return (
      <div className="card">
        <div className="label" style={{ width: '100%' }}>
          <SkeletonLoader width={80} height={16} className="mb-1" />
        </div>
        <div className="value" style={{ width: '60%' }}>
          <SkeletonLoader width={120} height={24} className="mb-1" />
        </div>
        <div className="change" style={{ width: '100%' }}>
          <SkeletonLoader width={60} height={16} />
          <SkeletonLoader width={80} height={16} className="mt-1" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="label">Net worth</div>
        <div className="value text-error">Error loading data</div>
        <div className="change">
          <span aria-hidden="true" className="text-error">!</span>
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
        <div className="label">Net worth</div>
        <div className="value">—</div>
        <div className="change">
          <span aria-hidden="true">—</span>
          <span>—</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="label">Net worth</div>
      <div className="value">{value}</div>
      <div className="change">
        {/* Using Lucide icon placeholder */}
        <span aria-hidden="true">{isIncrease ? '↑' : '↓'}</span>
        <span>{change}</span>
      </div>
    </div>
  );
};