import React from 'react';
import { Layers, UploadCloud, History, PlayCircle, CheckCircle, AlertTriangle, Home } from 'lucide-react';
import { RunSummary } from '../types';

interface NavbarProps {
  currentView: 'landing' | 'upload' | 'dashboard' | 'history';
  setCurrentView: (view: 'landing' | 'upload' | 'dashboard' | 'history') => void;
  activeRun?: RunSummary | null;
  onLoadDemo: () => void;
  isDemoLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  setCurrentView,
  activeRun,
  onLoadDemo,
  isDemoLoading,
}) => {
  const getStatusBadge = () => {
    if (!activeRun) return null;
    const status = activeRun.status;
    if (status === 'completed') {
      return (
        <span className="badge badge-green flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          Completed
        </span>
      );
    }
    if (status === 'inconclusive') {
      return (
        <span className="badge badge-amber flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          Inconclusive — insufficient reliable matches
        </span>
      );
    }
    if (status === 'failed') {
      return (
        <span className="badge badge-red flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          Failed
        </span>
      );
    }
    // Running stages
    return (
      <span className="badge badge-blue flex items-center gap-1.5 animate-pulse">
        <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
        {activeRun.stage_message || status}
      </span>
    );
  };

  return (
    <header className="bg-slate-950/90 text-white border-b border-slate-800/80 backdrop-blur-md shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-15 flex items-center justify-between">
        {/* Brand / Logo */}
        <div
          onClick={() => setCurrentView('landing')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="p-1.5 rounded-lg bg-slate-900 border border-slate-700/60 shadow-sm flex items-center justify-center text-blue-400 group-hover:border-blue-500/50 transition-colors">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-5 h-5">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.25" strokeOpacity="0.4" />
              <path
                d="M12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21C9.8 18.2 9 15.2 9 12C9 8.8 9.8 5.8 12 3Z"
                fill="currentColor"
                fillOpacity="0.9"
              />
              <circle cx="16" cy="12" r="1.5" fill="#60a5fa" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-light tracking-[0.22em] text-white uppercase group-hover:text-blue-400 transition-colors leading-none">
                LunarAlign
              </h1>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Lunar Image Registration and Analysis
            </p>
          </div>
        </div>

        {/* Center: Run status badge (only when relevant run active) */}
        <div className="hidden md:flex items-center gap-2">
          {activeRun && getStatusBadge()}
        </div>

        {/* Right Navigation Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentView('landing')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              currentView === 'landing'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Home className="w-3.5 h-3.5" />
            Home
          </button>

          <button
            onClick={() => setCurrentView('upload')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              currentView === 'upload'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Upload
          </button>

          <button
            onClick={() => setCurrentView('dashboard')}
            disabled={!activeRun}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              currentView === 'dashboard'
                ? 'bg-blue-600 text-white shadow-sm'
                : activeRun
                ? 'text-slate-300 hover:bg-slate-800 hover:text-white'
                : 'text-slate-600 opacity-50 cursor-not-allowed'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Dashboard
          </button>

          <button
            onClick={() => setCurrentView('history')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              currentView === 'history'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            History
          </button>

          <div className="h-5 w-px bg-slate-800 mx-1" />

          {/* Single Clearly Labelled Load Demo Button */}
          <button
            onClick={onLoadDemo}
            disabled={isDemoLoading}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/90 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-sm shadow-emerald-600/20 transition-all disabled:opacity-50"
            title="Load Bundled Chandrayaan-2 OHRC and LRO NAC Demo Pair"
          >
            <PlayCircle className="w-3.5 h-3.5" />
            {isDemoLoading ? 'Loading...' : 'Load Demo'}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
