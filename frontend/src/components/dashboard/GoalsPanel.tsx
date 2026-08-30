import React from 'react';
import { GoalItem } from './GoalItem';

interface GoalsPanelProps {
  goals: Array<{
    name: string;
    percentage: number;
  }>;
}

export const GoalsPanel: React.FC<GoalsPanelProps> = ({ goals }) => {
  return (
    <div className="panel">
      <h3>Goals</h3>
      <div className="goals-list">
        {goals.map((goal, index) => (
          <GoalItem
            key={index}
            name={goal.name}
            percentage={goal.percentage}
          />
        ))}
      </div>
    </div>
  );
};