import React from 'react';
import { CheckCircle2, CircleAlert, X } from 'lucide-react';

interface ToastProps {
  message: string;
  tone: 'success' | 'error';
  onDismiss: () => void;
  action?: React.ReactNode;
}

const Toast: React.FC<ToastProps> = ({ message, tone, onDismiss, action }) => (
  <div className={`app-toast ${tone === 'success' ? 'agent-success' : 'agent-error'}`} role={tone === 'error' ? 'alert' : 'status'}>
    {tone === 'success' ? <CheckCircle2 aria-hidden="true"/> : <CircleAlert aria-hidden="true"/>}
    <span>{message}</span>
    {action}
    <button type="button" className="toast-dismiss" aria-label="Dismiss notification" onClick={onDismiss}>
      <X aria-hidden="true"/>
    </button>
  </div>
);

export default Toast;
