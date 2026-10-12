import React, { useState, useEffect } from 'react';
import { RunSummary } from '../types';
import { History, Clock, CheckCircle2, AlertTriangle, XCircle, ArrowRight, RefreshCw } from 'lucide-react';

interface HistoryViewProps {
  onSelectRun: (runId: string) => void;
  activeRunId?: string;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ onSelectRun, activeRunId }) => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchRuns = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/runs');
      if (res.ok) {
        const data = await res.json();
        setRuns(data.runs || []);
      }
    } catch (e) {
      console.error('Failed to load runs history:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const getStatusBadge = (status: string) => {
    if (status === 'completed') {
      return (
        <span className="badge badge-green flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5" /> Completed
        </span>
      );
    }
    if (status === 'inconclusive') {
      return (
        <span className="badge badge-amber flex items-center gap-1">
          <AlertTriangle className="w-3.5 h-3.5" /> Inconclusive
        </span>
      );
    }
    if (status === 'failed') {
      return (
        <span className="badge badge-red flex items-center gap-1">
          <XCircle className="w-3.5 h-3.5" /> Failed
        </span>
      );
    }
    return (
      <span className="badge badge-blue flex items-center gap-1 animate-pulse">
        <Clock className="w-3.5 h-3.5" /> {status}
      </span>
    );
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Saved Comparison Runs History</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Select any prior execution to restore the full metrics report, alignments and visual artifacts without recalculation.
          </p>
        </div>
        <button
          onClick={fetchRuns}
          className="p-2 text-slate-300 hover:text-white bg-slate-900 border border-slate-800 rounded-lg shadow-xs hover:bg-slate-800 transition-colors"
          title="Refresh History"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-slate-400 text-xs">Loading saved comparison runs...</div>
      ) : runs.length === 0 ? (
        <div className="card p-8 bg-slate-900 border-slate-800 text-center text-slate-400 text-xs">
          No comparison runs found. Perform a new upload or run the Instant Lunar Demo to see records.
        </div>
      ) : (
        <div className="card bg-slate-900/90 overflow-hidden border border-slate-800 shadow-md">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-300 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Run ID / Timestamp</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Source Image</th>
                  <th className="py-3 px-4">Reference Image</th>
                  <th className="py-3 px-4">Verified Inliers</th>
                  <th className="py-3 px-4">Median Residual</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono">
                {runs.map((r) => {
                  const isCurrent = r.id === activeRunId;
                  const dateStr = new Date(r.created_at).toLocaleString();
                  return (
                    <tr
                      key={r.id}
                      className={`hover:bg-slate-800/50 transition-colors ${isCurrent ? 'bg-blue-950/30' : ''}`}
                    >
                      <td className="py-3 px-4">
                        <div className="font-bold text-white">{r.id}</div>
                        <div className="text-[10px] text-slate-400 font-sans">{dateStr}</div>
                      </td>
                      <td className="py-3 px-4 font-sans">{getStatusBadge(r.status)}</td>
                      <td className="py-3 px-4 text-slate-300 truncate max-w-[140px]">{r.source_filename}</td>
                      <td className="py-3 px-4 text-slate-300 truncate max-w-[140px]">{r.reference_filename}</td>
                      <td className="py-3 px-4 font-bold text-emerald-400">
                        {r.inlier_count !== null && r.inlier_count !== undefined ? r.inlier_count : '—'}
                      </td>
                      <td className="py-3 px-4 font-bold text-blue-400">
                        {r.median_residual !== null && r.median_residual !== undefined
                          ? `${r.median_residual.toFixed(2)} px`
                          : '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-sans">
                        <button
                          onClick={() => onSelectRun(r.id)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ml-auto transition-all ${
                            isCurrent
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-800 hover:bg-blue-600 hover:text-white text-slate-300'
                          }`}
                        >
                          {isCurrent ? 'Viewing' : 'Open Results'}
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
