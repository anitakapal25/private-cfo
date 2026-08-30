import React from 'react';

interface FinancialHealthScoreProps {
  score: number;
  maxScore?: number;
}

export const FinancialHealthScore: React.FC<FinancialHealthScoreProps> = ({
  score,
  maxScore = 100
}) => {
  return (
    <div className="score-card">
      <div className="value">{score} / {maxScore}</div>
      <div className="label">Financial health score</div>
    </div>
  );
};