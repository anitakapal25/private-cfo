import React, { useEffect, useId, useRef, useState } from 'react';
import { Info } from 'lucide-react';

interface InfoTooltipProps {
  term: string;
  explanation: string;
  example?: string;
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({ term, explanation, example }) => {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const closeOnOutsideClick = (event: MouseEvent | TouchEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        root.current?.querySelector<HTMLButtonElement>('button')?.focus();
      }
    };
    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('touchstart', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('touchstart', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open]);

  return (
    <span
      className={`info-tooltip ${open ? 'is-open' : ''}`}
      ref={root}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="info-tooltip-trigger"
        aria-label={`Explain ${term}`}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        <Info aria-hidden="true" />
      </button>
      <span className="info-tooltip-content" id={id} role="tooltip" aria-hidden={!open}>
        {explanation}{example && <span className="info-tooltip-example">Example: {example}</span>}
      </span>
    </span>
  );
};

export default InfoTooltip;
