import React from 'react';
import { CosmicParallaxBg } from '@/components/ui/parallax-cosmic-background';
import { ArrowRight, History, PlayCircle } from 'lucide-react';

interface LandingPageProps {
  onStartUpload: () => void;
  onViewHistory: () => void;
  onLoadDemo: () => void;
  isDemoLoading: boolean;
}

// Restrained original geometric icon for LunarAlign
export const LunarAlignLogo: React.FC<{ className?: string }> = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.25" strokeOpacity="0.4" />
    <path
      d="M12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21C9.8 18.2 9 15.2 9 12C9 8.8 9.8 5.8 12 3Z"
      fill="currentColor"
      fillOpacity="0.9"
    />
    <circle cx="16" cy="12" r="1.5" fill="#60a5fa" />
  </svg>
);

export const LandingPage: React.FC<LandingPageProps> = ({
  onStartUpload,
  onViewHistory,
  onLoadDemo,
  isDemoLoading,
}) => {
  return (
    <div className="relative min-h-screen w-full flex flex-col bg-[#000104]">
      {/* Compact Navigation Bar */}
      <nav className="absolute top-0 inset-x-0 z-40 flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
        <div className="flex items-center gap-2.5 text-slate-200">
          <LunarAlignLogo className="w-5 h-5 text-blue-400" />
          <span className="text-xs font-light tracking-[0.25em] text-slate-200 uppercase">
            LunarAlign
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onStartUpload}
            className="px-3.5 py-1.5 rounded-lg text-xs font-normal text-slate-300 hover:text-white hover:bg-slate-800/60 border border-slate-800/80 hover:border-slate-700 backdrop-blur-xs transition-all flex items-center gap-1.5"
          >
            Start Comparison
          </button>
          <button
            onClick={onViewHistory}
            className="px-3.5 py-1.5 rounded-lg text-xs font-normal text-slate-300 hover:text-white hover:bg-slate-800/60 border border-slate-800/80 hover:border-slate-700 backdrop-blur-xs transition-all flex items-center gap-1.5"
          >
            <History className="w-3.5 h-3.5 text-slate-400" />
            Run History
          </button>
          <button
            onClick={onLoadDemo}
            disabled={isDemoLoading}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-blue-300 hover:text-white bg-blue-950/60 hover:bg-blue-900/80 border border-blue-800/50 hover:border-blue-700 backdrop-blur-xs transition-all flex items-center gap-1.5 disabled:opacity-50"
            title="Load Bundled OHRC & LRO NAC Demo Pair"
          >
            <PlayCircle className="w-3.5 h-3.5 text-blue-400" />
            {isDemoLoading ? 'Loading...' : 'Load Demo'}
          </button>
        </div>
      </nav>

      {/* Main Cosmic Parallax Background with Authoritative Horizon & Title */}
      <CosmicParallaxBg
        head="LUNARALIGN"
        text="REGISTER · MATCH · ANALYZE"
        loop={true}
        className="flex-1"
      >
        {/* Understated hero action below feature text */}
        <button
          onClick={onStartUpload}
          className="group px-4 py-2 rounded-lg text-[11px] uppercase tracking-[0.18em] font-normal text-slate-400 hover:text-slate-100 bg-slate-950/80 hover:bg-slate-900 border border-slate-800 hover:border-slate-600 backdrop-blur-xs transition-all flex items-center gap-2 shadow-sm"
        >
          <span>Start Comparison</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" />
        </button>
      </CosmicParallaxBg>
    </div>
  );
};

export default LandingPage;
