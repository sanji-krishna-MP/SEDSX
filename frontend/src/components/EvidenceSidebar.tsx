import React, { useState } from 'react';
import { MetricDetail, RunSummary } from '../types';
import { Compass, ChevronRight, Info } from 'lucide-react';

interface EvidenceSidebarProps {
  metrics: MetricDetail[];
  run: RunSummary;
  onSelectMetric: (metric: MetricDetail) => void;
}

export const EvidenceSidebar: React.FC<EvidenceSidebarProps> = ({
  metrics,
  run,
  onSelectMetric
}) => {
  const [showObsDrawer, setShowObsDrawer] = useState(false);

  const getMetric = (code: string) => metrics.find(m => m.metric_code === code && m.stage === 'comparison');

  const c1 = getMetric('C1');
  const c2 = getMetric('C2');
  const c3 = getMetric('C3');
  const c4 = getMetric('C4');
  const c5 = getMetric('C5');
  const c6 = getMetric('C6');
  const c7 = getMetric('C7');
  const c8 = getMetric('C8');
  const c9 = getMetric('C9');
  const c10 = getMetric('C10');
  const c11 = getMetric('C11');

  const renderMetricCard = (m?: MetricDetail, priorityBadge?: string) => {
    if (!m) return null;

    const isAvailable = m.availability && m.display_index !== null;
    const score = m.display_index ?? 0;

    let scoreColor = 'text-blue-400';
    let barColor = 'bg-blue-500';
    if (score >= 70) {
      scoreColor = 'text-emerald-400';
      barColor = 'bg-emerald-500';
    } else if (score < 40) {
      scoreColor = 'text-amber-400';
      barColor = 'bg-amber-500';
    }

    return (
      <div
        onClick={() => onSelectMetric(m)}
        className="p-3 bg-slate-900/90 rounded-xl border border-slate-800/90 hover:border-blue-500/60 hover:shadow-md hover:shadow-blue-900/20 cursor-pointer transition-all group"
      >
        <div className="flex items-start justify-between gap-1 mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] font-bold text-slate-400 bg-slate-800/90 px-1.5 py-0.5 rounded border border-slate-700/60">
              {m.metric_code}
            </span>
            <span className="text-xs font-semibold text-slate-100 group-hover:text-blue-300 transition-colors">
              {m.name}
            </span>
          </div>
          {priorityBadge && (
            <span className="text-[10px] font-medium text-slate-400 bg-slate-800/60 px-1.5 py-0.5 rounded border border-slate-700/50">
              {priorityBadge}
            </span>
          )}
        </div>

        <div className="flex items-baseline justify-between mt-1">
          <div className="flex items-baseline gap-1">
            {isAvailable ? (
              <>
                <span className="text-base font-bold text-white font-mono">
                  {m.raw_value !== null ? m.raw_value : '—'}
                </span>
                <span className="text-xs text-slate-400">{m.raw_unit}</span>
              </>
            ) : (
              <span className="text-xs font-medium text-slate-500 italic">
                {m.unavailable_reason || 'Not available'}
              </span>
            )}
          </div>

          {isAvailable && (
            <div className="text-right">
              <span className={`text-sm font-bold font-mono ${scoreColor}`}>
                {score.toFixed(1)}
              </span>
              <span className="text-[10px] text-slate-500">/100</span>
            </div>
          )}
        </div>

        {isAvailable && (
          <div className="mt-2">
            <div className="progress-bar-bg bg-slate-800">
              <div
                className={`progress-bar-fill ${barColor}`}
                style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }}
              />
            </div>
            <div className="flex justify-between items-center mt-1 text-[10px] text-slate-400">
              <span className="truncate pr-1">{m.index_label}</span>
              <ChevronRight className="w-3 h-3 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <aside className="w-80 bg-slate-950/70 border-r border-slate-800 flex flex-col h-full overflow-y-auto p-4 shrink-0">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Registration Evidence
          </h2>
          <p className="text-[11px] text-slate-500">Eleven Comparison Indicators</p>
        </div>
        <button
          onClick={() => setShowObsDrawer(!showObsDrawer)}
          className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 bg-blue-950/40 px-2 py-1 rounded border border-blue-800/60 transition-colors"
          title="Observation Geometry Details"
        >
          <Compass className="w-3.5 h-3.5" />
          Metadata
        </button>
      </div>

      {/* Observation Drawer */}
      {showObsDrawer && (
        <div className="mb-4 p-3 bg-slate-900 border border-blue-900/60 rounded-xl text-xs space-y-2 animate-fadeIn">
          <div className="flex justify-between items-center font-bold text-blue-300 border-b border-slate-800 pb-1">
            <span>Observation Support Metadata</span>
            <button onClick={() => setShowObsDrawer(false)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          <div className="text-[11px] text-slate-400 space-y-1 font-mono">
            <div>• Modes: <span className="font-semibold text-slate-200">{run.modes.join(', ')}</span></div>
            <div>• Dimensions: Src {run.source_dims?.[1]}×{run.source_dims?.[0]} | Ref {run.ref_dims?.[1]}×{run.ref_dims?.[0]}</div>
            <div>• Source GSD: <span className="text-slate-200">0.25 m/px (OHRC)</span></div>
            <div>• Ref GSD: <span className="text-slate-200">0.50 m/px (LRO NAC)</span></div>
            <div>• Coordinate Frame: Lunar Local ENU</div>
          </div>
        </div>
      )}

      {/* Primary Evidence Groups */}
      <div className="space-y-2.5">
        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1">
          Geometric Support & Overlap
        </div>
        {renderMetricCard(c1, 'Coverage')}
        {renderMetricCard(c2, 'Usable Area')}

        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1 pt-2">
          Feature Correspondences
        </div>
        {renderMetricCard(c3, 'Proposed')}
        {renderMetricCard(c4, 'Accepted')}
        {renderMetricCard(c5, 'Agreement')}
        {renderMetricCard(c6, 'Dispersion')}

        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1 pt-2">
          Geometric Residuals & Accuracy
        </div>
        {renderMetricCard(c7, 'Fitting Error')}
        {renderMetricCard(c8, 'Independent Check')}

        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1 pt-2">
          Observation Conditions (Supporting)
        </div>
        {renderMetricCard(c9, 'Illumination')}
        {renderMetricCard(c10, 'Sun Angle')}
        {renderMetricCard(c11, 'Scale Ratio')}
      </div>

      <div className="mt-4 p-2.5 rounded-lg bg-slate-900 text-[11px] text-slate-400 border border-slate-800">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300 mb-0.5">
          <Info className="w-3.5 h-3.5 text-blue-400" />
          Display Index Policy
        </div>
        Indicators (out of 100) describe geometric and illumination consistency. They are not probabilistic accuracy percentages.
      </div>
    </aside>
  );
};

export default EvidenceSidebar;
