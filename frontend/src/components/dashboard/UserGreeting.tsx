import React from 'react';

interface UserGreetingProps {
  name: string;
}

export const UserGreeting: React.FC<UserGreetingProps> = ({ name }) => {
  return (
    <div>
      <div className="greeting-title">Good morning, {name}</div>
      <div className="sub">Here is what changed since your last check‑in.</div>
    </div>
  );
};