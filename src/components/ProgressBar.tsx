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
      className="fixed top-0 left-0 right-0 h-2 z-50 bg-slate-900/50 overflow-hidden"
      role="progressbar"
      aria-busy="true"
      aria-valuetext="Searching..."
    >
      {/* Wave animation container */}
      <div className="relative w-full h-full">
        {/* Wave 1 - Primary */}
        <div
          className="absolute inset-0 opacity-80"
          style={{
            background: 'linear-gradient(90deg, transparent, #22d3ee, #0891b2, #22d3ee, transparent)',
            animation: 'wave 1.2s ease-in-out infinite',
          }}
        />
        {/* Wave 2 - Secondary (offset) */}
        <div
          className="absolute inset-0 opacity-60"
          style={{
            background: 'linear-gradient(90deg, transparent, #06b6d4, #0e7490, #06b6d4, transparent)',
            animation: 'wave 1.2s ease-in-out infinite 0.3s',
          }}
        />
        {/* Wave 3 - Accent */}
        <div
          className="absolute inset-0 opacity-40"
          style={{
            background: 'linear-gradient(90deg, transparent, #67e8f9, #22d3ee, #67e8f9, transparent)',
            animation: 'wave 1.2s ease-in-out infinite 0.6s',
          }}
        />
      </div>

      {/* CSS Keyframes */}
      <style>{`
        @keyframes wave {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
};

export default ProgressBar;
