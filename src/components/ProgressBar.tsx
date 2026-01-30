import React from 'react';

interface ProgressBarProps {
  isLoading: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ isLoading }) => {
  if (!isLoading) {
    return null;
  }

  return (
    <div 
      className="fixed top-0 left-0 right-0 h-1 z-50 bg-sky-900/30 overflow-hidden" 
      role="progressbar" 
      aria-busy="true" 
      aria-valuetext="Loading..."
    >
      <div className="relative w-full h-full">
        <div className="absolute top-0 bottom-0 left-0 w-full h-full bg-gradient-to-r from-transparent via-sky-400 to-transparent animate-shimmer"></div>
      </div>
    </div>
  );
};

export default ProgressBar;
