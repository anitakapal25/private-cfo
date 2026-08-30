import React from 'react';
import Icon from '@/components/ui/Icon';
import Button from '@/components/ui/Button';

interface AskArthaPanelProps {
  placeholder?: string;
  buttonText?: string;
  chips: string[];
}

export const AskArthaPanel: React.FC<AskArthaPanelProps> = ({
  placeholder = 'Ask about your finances…',
  buttonText = 'Send',
  chips = []
}) => {
  const handleSend = () => {
    // In a real implementation, this would get the input value and call onSend
    alert('Send button clicked');
  };

  return (
    <div className="panel ask-panel">
      <h3>Ask Artha</h3>
      <p>Can I afford a ₹20L home down payment in three years without delaying my retirement?</p>
      <div style={{ display: 'flex', gap: '.5rem', alignItems: 'end' }}>
        <label htmlFor="ask-artha-input" className="sr-only">
          Ask Artha question
        </label>
        <input
          id="ask-artha-input"
          type="text"
          placeholder={placeholder}
          className="flex-1 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-action"
        />
        <Button variant="primary" onClick={handleSend}>
          {buttonText}
        </Button>
      </div>
      <div className="chips">
        {chips.map((chip, index) => (
          <div key={index} className="chip" onClick={() => alert(`Clicked: ${chip}`)}>
            {chip}
          </div>
        ))}
      </div>
      <div style={{ marginTop: '.5rem', fontSize: '.75rem', color: 'var(--color-text-secondary)' }}>
        <Icon name="shield-check" size={16} />
        <span> Calculations use verified inputs and visible assumptions.</span>
      </div>
    </div>
  );
};