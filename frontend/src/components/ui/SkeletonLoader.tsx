import React from 'react';

interface SkeletonLoaderProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  radius?: string;
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  width = '100%',
  height = '1rem',
  className = '',
  radius = '4px'
}) => {
  return (
    <div
      className={`skeleton-loader ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        borderRadius: radius,
        backgroundColor: '#e2e8f0',
        backgroundImage:
          'linear-gradient(90deg, #e2e8f0, #f0f4f8, #e2e8f0)',
        backgroundSize: '200% 100%',
        animation: 'loading 1.5s infinite',
      }}
    />
  );
};

export default SkeletonLoader;