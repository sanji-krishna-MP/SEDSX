import React, { useState } from 'react';
import { MetricDetail, MatchPoint, CheckpointRecord, RunSummary } from '../types';
import { BarChart3, Calculator, GitPullRequest, Settings, ChevronDown, ChevronUp, CheckCircle, XCircle, Info, ExternalLink } from 'lucide-react';

interface MetricsTabsProps {
  metrics: MetricDetail[];
  matches?: MatchPoint[];
  checkpoints?: CheckpointRecord[];
  run: RunSummary;
  onSelectMetric: (metric: MetricDetail) => void;
}

export const MetricsTabs: React.FC<MetricsTabsProps> = ({
  metrics,
  matches = [],
  checkpoints = [],
  run,
  onSelectMetric
}) => {
  const [activeTab, setActiveTab] = useState<'preprocessing' | 'comparison' | 'matches' | 'details'>('preprocessing');
  const [expandedHistogram, setExpandedHistogram] = useState(false);
  const [expandedPercentiles, setExpandedPercentiles] = useState(false);
  const [matchFilter, setMatchFilter] = useState<'all' | 'inliers' | 'outliers'>('all');

  // Preprocessing metrics P1 to P9
  const prepCodes = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'];
  const srcPrep = metrics.filter(m => m.stage === 'preprocessing' && m.image_role === 'source');
  const refPrep = metrics.filter(m => m.stage === 'preprocessing' && m.image_role === 'reference');

  // Comparison metrics C1 to C11
  const compMetrics = metrics.filter(m => m.stage === 'comparison');

  const getMetricPair = (code: string) => {
    const s = srcPrep.find(m => m.metric_code === code);
    const r = refPrep.find(m => m.metric_code === code);
    return { s, r };
  };

  const filteredMatches = matches.filter(m => {
    if (matchFilter === 'inliers') return m.is_inlier;
    if (matchFilter === 'outliers') return !m.is_inlier;
    return true;
  });

  return (
    <div className="card bg-slate-900/90 mt-4 overflow-hidden border border-slate-800 text-slate-200">
      {/* Tab Navigation */}
      <div className="flex border-b border-slate-800 bg-slate-950 px-4 pt-2 gap-2 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('preprocessing')}
          className={`px-4 py-2.5 border-b-2 flex items-center gap-2 transition-all ${
            activeTab === 'preprocessing'
              ? 'border-blue-500 text-blue-400 bg-slate-900 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Preprocessing Metrics (9 Types)
        </button>

        <button
          onClick={() => setActiveTab('comparison')}
          className={`px-4 py-2.5 border-b-2 flex items-center gap-2 transition-all ${
            activeTab === 'comparison'
              ? 'border-blue-500 text-blue-400 bg-slate-900 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calculator className="w-4 h-4" />
          Comparison Calculations (11 Types)
        </button>

        <button
          onClick={() => setActiveTab('matches')}
          className={`px-4 py-2.5 border-b-2 flex items-center gap-2 transition-all ${
            activeTab === 'matches'
              ? 'border-blue-500 text-blue-400 bg-slate-900 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <GitPullRequest className="w-4 h-4" />
          Match Evidence ({matches.length} Candidates)
        </button>

        <button
          onClick={() => setActiveTab('details')}
          className={`px-4 py-2.5 border-b-2 flex items-center gap-2 transition-all ${
            activeTab === 'details'
              ? 'border-blue-500 text-blue-400 bg-slate-900 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Settings className="w-4 h-4" />
          Run Details & Diagnostics
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {/* TAB 1: PREPROCESSING METRICS */}
        {activeTab === 'preprocessing' && (
          <div className="space-y-4">
            <div className="text-xs text-slate-400 flex items-center justify-between">
              <span>9 Preprocessing statistics evaluated independently for Source (OHRC) and Reference (LRO NAC) before percentile stretching.</span>
              <span className="font-mono text-[11px] text-slate-500">Section 4 & 5 Formulas</span>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/90 text-slate-300 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Code</th>
                    <th className="py-2.5 px-3">Metric Name</th>
                    <th className="py-2.5 px-3">Source (OHRC)</th>
                    <th className="py-2.5 px-3">Reference (LRO)</th>
                    <th className="py-2.5 px-3">Difference</th>
                    <th className="py-2.5 px-3">Src Index / 100</th>
                    <th className="py-2.5 px-3">Ref Index / 100</th>
                    <th className="py-2.5 px-3 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono">
                  {prepCodes.map(code => {
                    const { s, r } = getMetricPair(code);
                    if (!s && !r) return null;
                    const name = s?.name || r?.name || code;
                    const sVal = s?.raw_value;
                    const rVal = r?.raw_value;
                    const unit = s?.raw_unit || '';
                    const diff = sVal !== null && sVal !== undefined && rVal !== null && rVal !== undefined
                      ? (sVal - rVal).toFixed(2)
                      : '—';

                    return (
                      <React.Fragment key={code}>
                        <tr
                          onClick={() => s && onSelectMetric(s)}
                          className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                        >
                          <td className="py-2.5 px-3 font-bold text-blue-400">{code}</td>
                          <td className="py-2.5 px-3 font-sans font-medium text-slate-200">{name}</td>
                          <td className="py-2.5 px-3 text-slate-100 font-semibold">
                            {sVal !== null && sVal !== undefined ? `${sVal} ${unit}` : 'Not available'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-100 font-semibold">
                            {rVal !== null && rVal !== undefined ? `${rVal} ${unit}` : 'Not available'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">{diff}</td>
                          <td className="py-2.5 px-3 font-bold text-emerald-400">
                            {s?.display_index !== null && s?.display_index !== undefined ? `${s.display_index.toFixed(1)}/100` : '—'}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-blue-400">
                            {r?.display_index !== null && r?.display_index !== undefined ? `${r.display_index.toFixed(1)}/100` : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {code === 'P4' ? (
                              <button
                                onClick={(e) => { e.stopPropagation(); setExpandedHistogram(!expandedHistogram); }}
                                className="text-[11px] text-blue-400 font-sans hover:underline flex items-center gap-0.5 ml-auto"
                              >
                                {expandedHistogram ? 'Collapse' : 'Expand Plot'}
                                {expandedHistogram ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                              </button>
                            ) : code === 'P5' ? (
                              <button
                                onClick={(e) => { e.stopPropagation(); setExpandedPercentiles(!expandedPercentiles); }}
                                className="text-[11px] text-blue-400 font-sans hover:underline flex items-center gap-0.5 ml-auto"
                              >
                                {expandedPercentiles ? 'Collapse' : 'Percentiles'}
                                {expandedPercentiles ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                              </button>
                            ) : (
                              <span className="text-[11px] text-slate-500 font-sans group-hover:text-blue-400">View</span>
                            )}
                          </td>
                        </tr>

                        {/* Expandable Histogram Section */}
                        {code === 'P4' && expandedHistogram && s?.extra_data && r?.extra_data && (
                          <tr>
                            <td colSpan={8} className="p-4 bg-slate-900 border-t border-b border-slate-800 font-sans">
                              <div className="font-semibold text-xs text-slate-200 mb-2">
                                256-Bin Intensity Histogram Comparison (% per bin)
                              </div>
                              <div className="h-28 w-full flex items-end gap-0.5 bg-slate-950 p-2 rounded-lg border border-slate-800 overflow-x-auto">
                                {s.extra_data.percentages.map((sp: number, idx: number) => {
                                  const rp = r.extra_data?.percentages?.[idx] || 0;
                                  return (
                                    <div key={idx} className="flex-1 flex flex-col justify-end h-full min-w-[2px] group relative">
                                      <div
                                        style={{ height: `${Math.min(sp * 15, 100)}%` }}
                                        className="bg-emerald-400/80 w-full rounded-t-xs"
                                      />
                                      <div
                                        style={{ height: `${Math.min(rp * 15, 100)}%` }}
                                        className="bg-blue-400/80 w-full rounded-t-xs -mt-1"
                                      />
                                    </div>
                                  );
                                })}
                              </div>
                              <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                                <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-emerald-400 rounded" /> Source OHRC</span>
                                <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-blue-400 rounded" /> Reference LRO NAC</span>
                              </div>
                            </td>
                          </tr>
                        )}

                        {/* Expandable Percentiles Section */}
                        {code === 'P5' && expandedPercentiles && s?.extra_data && r?.extra_data && (
                          <tr>
                            <td colSpan={8} className="p-3 bg-slate-900 border-t border-b border-slate-800 font-sans">
                              <div className="grid grid-cols-3 gap-3 text-xs font-mono">
                                <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                                  <div className="text-[11px] text-slate-400 font-sans">Q0.01 (1st Percentile)</div>
                                  <div className="mt-1">Src: <b className="text-emerald-400">{s.extra_data['Q0.01']}</b> ({s.extra_data.indices[0].toFixed(1)}/100)</div>
                                  <div>Ref: <b className="text-blue-400">{r.extra_data['Q0.01']}</b> ({r.extra_data.indices[0].toFixed(1)}/100)</div>
                                </div>
                                <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                                  <div className="text-[11px] text-slate-400 font-sans">Q0.50 (Median)</div>
                                  <div className="mt-1">Src: <b className="text-emerald-400">{s.extra_data['Q0.50']}</b> ({s.extra_data.indices[1].toFixed(1)}/100)</div>
                                  <div>Ref: <b className="text-blue-400">{r.extra_data['Q0.50']}</b> ({r.extra_data.indices[1].toFixed(1)}/100)</div>
                                </div>
                                <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                                  <div className="text-[11px] text-slate-400 font-sans">Q0.99 (99th Percentile)</div>
                                  <div className="mt-1">Src: <b className="text-emerald-400">{s.extra_data['Q0.99']}</b> ({s.extra_data.indices[2].toFixed(1)}/100)</div>
                                  <div>Ref: <b className="text-blue-400">{r.extra_data['Q0.99']}</b> ({r.extra_data.indices[2].toFixed(1)}/100)</div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: COMPARISON CALCULATIONS */}
        {activeTab === 'comparison' && (
          <div className="space-y-4">
            <div className="text-xs text-slate-400 flex items-center justify-between">
              <span>Eleven Comparison metric types establishing geometric alignment, inlier agreement, spatial coverage and observation similarities.</span>
              <span className="font-mono text-[11px] text-slate-500">Click any row for formula drilldown</span>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/90 text-slate-300 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Code</th>
                    <th className="py-2.5 px-3">Metric Type</th>
                    <th className="py-2.5 px-3">Raw Value & Unit</th>
                    <th className="py-2.5 px-3">Display Index / 100</th>
                    <th className="py-2.5 px-3">Index Interpretation</th>
                    <th className="py-2.5 px-3">Status / Availability</th>
                    <th className="py-2.5 px-3 text-right">Formula</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono">
                  {compMetrics.map(m => {
                    const isAvail = m.availability && m.display_index !== null;
                    return (
                      <tr
                        key={m.metric_code}
                        onClick={() => onSelectMetric(m)}
                        className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                      >
                        <td className="py-2.5 px-3 font-bold text-blue-400">{m.metric_code}</td>
                        <td className="py-2.5 px-3 font-sans font-semibold text-slate-200">{m.name}</td>
                        <td className="py-2.5 px-3 text-slate-100 font-semibold">
                          {isAvail ? `${m.raw_value} ${m.raw_unit}` : <span className="text-slate-500 font-normal italic">Not available</span>}
                        </td>
                        <td className="py-2.5 px-3 font-bold text-blue-400">
                          {isAvail ? `${m.display_index?.toFixed(1)}/100` : '—'}
                        </td>
                        <td className="py-2.5 px-3 font-sans text-slate-400">{m.index_label}</td>
                        <td className="py-2.5 px-3 font-sans">
                          {isAvail ? (
                            <span className="badge badge-green flex items-center gap-1 w-fit">
                              <CheckCircle className="w-3 h-3" />
                              Computed
                            </span>
                          ) : (
                            <span className="badge badge-slate flex items-center gap-1 w-fit">
                              <Info className="w-3 h-3" />
                              {m.unavailable_reason || 'Unavailable'}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-sans text-blue-400 font-medium">
                          <span className="flex items-center gap-1 justify-end hover:underline">
                            Explain <ExternalLink className="w-3 h-3" />
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: MATCH EVIDENCE */}
        {activeTab === 'matches' && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-medium">Filter Correspondences:</span>
                <div className="flex bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs font-medium">
                  <button
                    onClick={() => setMatchFilter('all')}
                    className={`px-2.5 py-1 rounded transition-all ${matchFilter === 'all' ? 'bg-slate-800 shadow-xs text-blue-400' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    All ({matches.length})
                  </button>
                  <button
                    onClick={() => setMatchFilter('inliers')}
                    className={`px-2.5 py-1 rounded transition-all ${matchFilter === 'inliers' ? 'bg-slate-800 shadow-xs text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Inliers Only ({matches.filter(m => m.is_inlier).length})
                  </button>
                  <button
                    onClick={() => setMatchFilter('outliers')}
                    className={`px-2.5 py-1 rounded transition-all ${matchFilter === 'outliers' ? 'bg-slate-800 shadow-xs text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Outliers ({matches.filter(m => !m.is_inlier).length})
                  </button>
                </div>
              </div>

              {checkpoints.length > 0 && (
                <span className="badge badge-green">
                  {checkpoints.length} Independent Withheld Checkpoints Active
                </span>
              )}
            </div>

            {/* Match points table */}
            <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900 text-slate-300 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800 sticky top-0">
                  <tr>
                    <th className="py-2 px-3">#</th>
                    <th className="py-2 px-3">Source (x, y)</th>
                    <th className="py-2 px-3">Reference (x, y)</th>
                    <th className="py-2 px-3">Predicted Ref (x, y)</th>
                    <th className="py-2 px-3">Residual (px)</th>
                    <th className="py-2 px-3">Ambiguity Ratio</th>
                    <th className="py-2 px-3">Status / Diagnostic</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {filteredMatches.slice(0, 100).map(m => (
                    <tr key={m.match_index} className={m.is_inlier ? 'bg-emerald-950/20 hover:bg-emerald-950/40' : 'bg-rose-950/20 hover:bg-rose-950/40'}>
                      <td className="py-1.5 px-3 font-bold text-slate-500">{m.match_index + 1}</td>
                      <td className="py-1.5 px-3 text-slate-300">({m.source_x.toFixed(1)}, {m.source_y.toFixed(1)})</td>
                      <td className="py-1.5 px-3 text-slate-300">({m.ref_x.toFixed(1)}, {m.ref_y.toFixed(1)})</td>
                      <td className="py-1.5 px-3 text-slate-400">
                        {m.pred_ref_x !== null && m.pred_ref_x !== undefined
                          ? `(${m.pred_ref_x.toFixed(1)}, ${m.pred_ref_y?.toFixed(1)})`
                          : '—'}
                      </td>
                      <td className="py-1.5 px-3 font-semibold text-slate-200">
                        {m.residual !== null && m.residual !== undefined ? `${m.residual.toFixed(2)} px` : '—'}
                      </td>
                      <td className="py-1.5 px-3 text-slate-400">{m.ambiguity_ratio.toFixed(3)}</td>
                      <td className="py-1.5 px-3 font-sans">
                        {m.is_inlier ? (
                          <span className="text-emerald-400 font-semibold">Accepted Inlier</span>
                        ) : (
                          <span className="text-rose-400">{m.rejection_reason || 'Outlier'}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Checkpoints subtable if available */}
            {checkpoints.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-800">
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-2">
                  Withheld Independent Checkpoints (Excluded from fitting)
                </h4>
                <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900 text-slate-300 text-[10px] uppercase font-semibold">
                      <tr>
                        <th className="py-2 px-3">ID</th>
                        <th className="py-2 px-3">Source (x, y)</th>
                        <th className="py-2 px-3">True Ref (x, y)</th>
                        <th className="py-2 px-3">Fitted Pred (x, y)</th>
                        <th className="py-2 px-3">Independent Error (px)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {checkpoints.map((cp, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/60">
                          <td className="py-1.5 px-3 font-bold text-blue-400">{cp.checkpoint_id}</td>
                          <td className="py-1.5 px-3 text-slate-300">({cp.source_x.toFixed(1)}, {cp.source_y.toFixed(1)})</td>
                          <td className="py-1.5 px-3 text-slate-300">({cp.ref_x.toFixed(1)}, {cp.ref_y.toFixed(1)})</td>
                          <td className="py-1.5 px-3 text-slate-400">
                            {cp.pred_ref_x !== null && cp.pred_ref_x !== undefined
                              ? `(${cp.pred_ref_x.toFixed(1)}, ${cp.pred_ref_y?.toFixed(1)})`
                              : '—'}
                          </td>
                          <td className="py-1.5 px-3 font-bold text-emerald-400">
                            {cp.residual !== null && cp.residual !== undefined ? `${cp.residual.toFixed(2)} px` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: RUN DETAILS & DIAGNOSTICS */}
        {activeTab === 'details' && (
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <div className="font-bold text-slate-200 mb-2 uppercase text-[11px] font-sans">
                  Pipeline Execution Timing (ms)
                </div>
                <div className="space-y-1.5">
                  {Object.entries(run.timing_ms || {}).map(([stage, ms]) => (
                    <div key={stage} className="flex justify-between border-b border-slate-800/80 pb-0.5">
                      <span className="capitalize text-slate-400">{stage}:</span>
                      <span className="font-bold text-slate-100">{ms} ms</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                <div className="font-bold text-slate-200 mb-2 uppercase text-[11px] font-sans">
                  Algorithmic Parameters & Anchors
                </div>
                <div className="space-y-1.5">
                  <div className="flex justify-between border-b border-slate-800/80 pb-0.5">
                    <span className="text-slate-400">Error scale anchor e0:</span>
                    <span className="font-bold text-slate-100">{run.config?.error_scale_e0 || 1.0} px</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/80 pb-0.5">
                    <span className="text-slate-400">Checkpoint anchor r0:</span>
                    <span className="font-bold text-slate-100">{run.config?.error_scale_r0 || 1.0} px</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/80 pb-0.5">
                    <span className="text-slate-400">Ratio filter cutoff:</span>
                    <span className="font-bold text-slate-100">{run.config?.match_ratio_thresh || 0.75}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/80 pb-0.5">
                    <span className="text-slate-400">Geometric reprojection cutoff:</span>
                    <span className="font-bold text-slate-100">{run.config?.ransac_reproj_thresh || 3.0} px</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800/80 pb-0.5">
                    <span className="text-slate-400">Spatial grid shape:</span>
                    <span className="font-bold text-slate-100">{run.config?.grid_rows || 4} × {run.config?.grid_cols || 4}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Warnings log */}
            {run.warnings && run.warnings.length > 0 && (
              <div className="p-3 bg-amber-950/30 border border-amber-600/40 rounded-xl font-sans">
                <div className="font-bold text-amber-300 text-xs mb-1">Operational Diagnostics & Warnings:</div>
                <ul className="list-disc list-inside text-xs text-amber-200/90 space-y-0.5">
                  {run.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
