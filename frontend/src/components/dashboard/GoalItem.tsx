import React from 'react';

interface GoalItemProps {
  name: string;
  percentage: number;
}

export const GoalItem: React.FC<GoalItemProps> = ({ name, percentage }) => {
  return (
    <div className="goal-row">
      <div className="info">
        <span className="name">{name}</span>
        <span className="percentage">{percentage}%</span>
      </div>
      <div className="bar">
        <div className="fill" style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
};