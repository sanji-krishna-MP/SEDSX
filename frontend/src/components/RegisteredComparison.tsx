import React, { useState, useRef, useEffect } from 'react';
import { Sliders, Flame, GitCommit, ArrowUpRight, Maximize2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { RunSummary } from '../types';

interface RegisteredComparisonProps {
  run: RunSummary;
  assets: Record<string, string>;
}

export const RegisteredComparison: React.FC<RegisteredComparisonProps> = ({ run, assets }) => {
  const [mode, setMode] = useState<'curtain' | 'difference' | 'matches' | 'residuals'>('curtain');
  const [sliderPos, setSliderPos] = useState<number>(50); // percentage 0..100
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [zoomToOverlap, setZoomToOverlap] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle curtain divider dragging
  const handleMouseDown = () => setIsDragging(true);
  const handleMouseUp = () => setIsDragging(false);

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.clientX;
    const offsetX = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (offsetX / rect.width) * 100));
    setSliderPos(pct);
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (!containerRef.current || e.touches.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.touches[0].clientX;
    const offsetX = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (offsetX / rect.width) * 100));
    setSliderPos(pct);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      window.addEventListener('touchmove', handleTouchMove);
      window.addEventListener('touchend', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleMouseUp);
    };
  }, [isDragging]);

  const rawRefImgUrl = assets.reference_preprocessed || `/api/runs/${run.id}/assets/reference_original`;
  const rawWarpedSrcUrl = assets.warped_source;

  const hasZoomedAssets = Boolean(assets.warped_source_zoomed && assets.reference_zoomed);
  const isZoomed = zoomToOverlap && hasZoomedAssets;

  const activeRefImgUrl = isZoomed ? assets.reference_zoomed : rawRefImgUrl;
  const activeWarpedSrcUrl = isZoomed ? assets.warped_source_zoomed : rawWarpedSrcUrl;

  const diffUrl = assets.appearance_diff;
  const matchesUrl = assets.matches_visualization;
  const residualsUrl = assets.residuals_map;

  const isAligned = run.status === 'completed' && Boolean(rawWarpedSrcUrl);

  return (
    <div className="card p-4 bg-slate-900/90 border-slate-800 flex flex-col">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${isAligned ? 'bg-emerald-500 shadow-emerald-500/50' : 'bg-amber-500 shadow-amber-500/50'} shadow-sm animate-pulse`} />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Registered Comparison View
          </h3>
          {isAligned ? (
            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Aligned
            </span>
          ) : (
            <span className="badge badge-amber text-xs font-medium flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              Inconclusive — insufficient reliable matches
            </span>
          )}
        </div>

        {/* Action Controls & Mode Selector Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Zoom to Overlap Toggle (Only when registered and zoomed assets available) */}
          {hasZoomedAssets && isAligned && (
            <button
              onClick={() => setZoomToOverlap(!zoomToOverlap)}
              className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 text-xs font-semibold border transition-all cursor-pointer ${
                isZoomed
                  ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-900/30'
                  : 'bg-slate-950 text-slate-300 hover:text-white border-slate-800 hover:border-slate-700'
              }`}
              title="Zoom comparison directly into the usable overlap bounding box"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              {isZoomed ? 'Full Reference View' : 'Zoom to Overlap'}
            </button>
          )}

          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
            <button
              onClick={() => setMode('curtain')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                mode === 'curtain'
                  ? 'bg-slate-800 text-blue-400 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Split Curtain
            </button>

            <button
              onClick={() => setMode('difference')}
              disabled={!diffUrl}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                mode === 'difference'
                  ? 'bg-slate-800 text-orange-400 shadow-sm'
                  : diffUrl
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-600 opacity-50 cursor-not-allowed'
              }`}
              title="Appearance difference |ref - warped_src| masked to usable overlap"
            >
              <Flame className="w-3.5 h-3.5" />
              Appearance Difference
            </button>

            <button
              onClick={() => setMode('matches')}
              disabled={!matchesUrl}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                mode === 'matches'
                  ? 'bg-slate-800 text-emerald-400 shadow-sm'
                  : matchesUrl
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-600 opacity-50 cursor-not-allowed'
              }`}
            >
              <GitCommit className="w-3.5 h-3.5" />
              Feature Correspondences
            </button>

            <button
              onClick={() => setMode('residuals')}
              disabled={!residualsUrl}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                mode === 'residuals'
                  ? 'bg-slate-800 text-cyan-400 shadow-sm'
                  : residualsUrl
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-600 opacity-50 cursor-not-allowed'
              }`}
            >
              <ArrowUpRight className="w-3.5 h-3.5" />
              Residual Arrows
            </button>
          </div>
        </div>
      </div>

      {/* Main Interactive Stage */}
      <div
        ref={containerRef}
        className="relative w-full aspect-16/9 max-h-[460px] bg-slate-950 rounded-xl overflow-hidden select-none border border-slate-800 flex items-center justify-center"
      >
        {mode === 'curtain' && (
          <>
            {/* Background Layer: Reference Image (Fixed Coordinate Grid) */}
            <img
              src={activeRefImgUrl}
              alt="Reference LRO"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
            />

            {/* Foreground Layer: Warped Source Image clipped by slider position */}
            {isAligned && activeWarpedSrcUrl ? (
              <>
                <div
                  className="absolute inset-0 overflow-hidden pointer-events-none"
                  style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
                >
                  <img
                    src={activeWarpedSrcUrl}
                    alt="Registered Source OHRC"
                    className="absolute inset-0 w-full h-full object-contain"
                  />
                </div>

                {/* Draggable Divider Line & Handle */}
                <div
                  onMouseDown={handleMouseDown}
                  onTouchStart={handleMouseDown}
                  className="curtain-handle"
                  style={{ left: `${sliderPos}%` }}
                >
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-[10px] font-mono px-1.5 py-0.5 rounded shadow">
                    {Math.round(sliderPos)}%
                  </div>
                </div>

                {/* Corner Labels */}
                <div className="absolute top-3 left-3 bg-slate-900/90 backdrop-blur-xs text-slate-200 text-xs px-2.5 py-1 rounded-md font-semibold border border-slate-700 pointer-events-none">
                  ◀ Reference — LRO NAC {isZoomed ? '(Zoomed)' : '(Fixed Grid)'}
                </div>
                <div className="absolute top-3 right-3 bg-emerald-950/90 backdrop-blur-xs text-emerald-300 text-xs px-2.5 py-1 rounded-md font-semibold border border-emerald-700/80 pointer-events-none">
                  Registered Source — OHRC {isZoomed ? '(Zoomed)' : '(Warped)'} ▶
                </div>
              </>
            ) : (
              /* Rich Diagnostic Inconclusive Notice - Tilted warp prevented */
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-slate-950/92 backdrop-blur-md z-10">
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl mb-3 shadow-lg">
                  <AlertTriangle className="w-8 h-8 text-amber-400" />
                </div>
                <h4 className="text-base font-bold text-amber-300 tracking-wide mb-1.5">
                  Inconclusive — insufficient reliable matches
                </h4>
                <p className="text-xs text-slate-300 max-w-lg leading-relaxed mb-4">
                  The alignment could not establish sufficient reliable geometric support ({run.candidate_count ?? 0} candidate matches, {run.inlier_count ?? 0} verified inliers; configurable support gate requires at least {run.config?.min_inliers ?? 6}). To prevent misleading geometric distortion, the tilted affine warp was suppressed.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <button
                    onClick={() => setMode('matches')}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-sm"
                  >
                    <GitCommit className="w-4 h-4" />
                    Inspect Candidate Matches
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {mode === 'difference' && diffUrl && (
          <div className="relative w-full h-full flex flex-col items-center justify-center">
            <img
              src={diffUrl}
              alt="Appearance Difference Map"
              className="w-full h-full object-contain"
            />
            <div className="absolute bottom-3 left-3 bg-slate-900/85 backdrop-blur-xs text-white text-xs px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-500" />
              <span>Appearance Difference (|I_ref - I_warped| in usable overlap). Illumination changes may cause appearance differences even with perfect alignment.</span>
            </div>
          </div>
        )}

        {mode === 'matches' && matchesUrl && (
          <div className="relative w-full h-full flex flex-col items-center justify-center">
            <img
              src={matchesUrl}
              alt="Correspondences SIFT"
              className="w-full h-full object-contain"
            />
            <div className="absolute bottom-3 left-3 bg-slate-900/85 backdrop-blur-xs text-white text-xs px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-3">
              <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                Accepted Inliers ({run.inlier_count ?? 0})
              </span>
              <span className="flex items-center gap-1 text-red-400 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                Rejected Pairs (Outliers)
              </span>
            </div>
          </div>
        )}

        {mode === 'residuals' && residualsUrl && (
          <div className="relative w-full h-full flex flex-col items-center justify-center">
            <img
              src={residualsUrl}
              alt="Residual Arrows Map"
              className="w-full h-full object-contain"
            />
            <div className="absolute bottom-3 left-3 bg-slate-900/85 backdrop-blur-xs text-white text-xs px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-cyan-400" />
              <span>Geometric Residual Error Vectors (Predicted to observed, magnified 3x). Median residual: {run.median_residual ?? '—'} px</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
