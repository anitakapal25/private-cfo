import React from 'react';
import { Lightbulb } from 'lucide-react';

interface PathToFreedomPanelProps {
  currentCorpus: string;
  targetCorpus: string;
  progressPercent: number;
  freedomDate: string;
}

export const PathToFreedomPanel: React.FC<PathToFreedomPanelProps> = ({
  currentCorpus,
  targetCorpus,
  progressPercent,
  freedomDate
}) => {
  return (
    <div className="panel">
      <h3>Your Path to Financial Freedom</h3>
      <p>Based on your verified data and current assumptions.</p>
      <div className="flex-gap-medium">
        <div><strong>Current corpus:</strong> {currentCorpus}</div>
        <div><strong>Target corpus:</strong> {targetCorpus}</div>
      </div>
      <div className="progress-bar" style={{ margin: '12px 0' }}>
        <div className="fill" style={{ width: `${progressPercent}%` }}></div>
      </div>
      <div>~{progressPercent}% completed – Estimated freedom date: {freedomDate}</div>
      <a href="#" className="text-primary-action font-medium inline-block mt-2">
        View calculation
      </a>
      <div className="recommendation mt-4">
        <div className="flex items-start">
          <Lightbulb className="h-4 w-4 text-primary-action mt-0.5 mr-2" aria-hidden="true" />
          <div>
            Increasing your monthly SIP by ₹10,000 could bring your financial-freedom estimate forward by ~1 yr 7 mo.
            <a href="#" className="text-primary-action font-medium">
              Review Scenario
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};