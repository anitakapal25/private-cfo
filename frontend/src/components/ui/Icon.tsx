import React from 'react';
import {
  Check,
  CheckCircle,
  CircleHelp,
  ClipboardType,
  Clock,
  Files,
  LayoutDashboard,
  ListChecks,
  Loader,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  UploadCloud,
  type LucideIcon,
} from 'lucide-react';

const icons: Record<string, LucideIcon> = {
  check: Check,
  'check-circle': CheckCircle,
  'circle-help': CircleHelp,
  'clipboard-type': ClipboardType,
  clock: Clock,
  files: Files,
  'layout-dashboard': LayoutDashboard,
  'list-checks': ListChecks,
  loader: Loader,
  'shield-check': ShieldCheck,
  'sliders-horizontal': SlidersHorizontal,
  target: Target,
  'upload-cloud': UploadCloud,
};

interface IconProps {
  name: string; // Lucide icon name
  size?: number | string;
  color?: string;
  className?: string;
}

const Icon: React.FC<IconProps> = ({
  name,
  size = 24,
  color = 'currentColor',
  className = ''
}) => {
  const IconComponent = icons[name] ?? CircleHelp;

  return (
    <IconComponent
      aria-hidden="true"
      className={className}
      size={size}
      color={color}
    />
  );
};

export default Icon;
