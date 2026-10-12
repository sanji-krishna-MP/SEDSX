import React from 'react';
import { MetricDetail } from '../types';
import { X, Calculator, Info, CheckCircle2, AlertCircle } from 'lucide-react';

interface FormulaModalProps {
  metric: MetricDetail | null;
  onClose: () => void;
}

export const FormulaModal: React.FC<FormulaModalProps> = ({ metric, onClose }) => {
  if (!metric) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-fadeIn">
      <div className="bg-slate-900 rounded-2xl shadow-2xl max-w-lg w-full border border-slate-800 overflow-hidden flex flex-col max-h-[90vh] text-slate-200">
        {/* Modal Header */}
        <div className="bg-slate-950 text-white p-4 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold bg-blue-600 px-2 py-0.5 rounded text-white shadow-xs">
              {metric.metric_code}
            </span>
            <div>
              <h3 className="text-sm font-bold leading-tight text-white">{metric.name}</h3>
              <p className="text-[11px] text-slate-400 capitalize">
                {metric.stage} • {metric.image_role} domain
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Formula Card */}
          <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-blue-400">
              <Calculator className="w-4 h-4 text-blue-400" />
              <span>Mathematical Formula</span>
            </div>
            <div className="font-mono text-sm bg-slate-900 p-2.5 rounded-lg border border-slate-800 text-cyan-300 overflow-x-auto shadow-inner">
              {metric.formula_text}
            </div>
          </div>

          {/* Substituted Actual Values */}
          <div className="space-y-2">
            <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[11px]">
              Substituted Actual Run Inputs
            </h4>
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono space-y-1">
              {Object.entries(metric.substituted_inputs || {}).map(([key, val]) => (
                <div key={key} className="flex justify-between items-center py-0.5 border-b border-slate-800/80 last:border-0">
                  <span className="text-slate-400">{key}:</span>
                  <span className="font-bold text-slate-200">{typeof val === 'number' ? val : String(val)}</span>
                </div>
              ))}
              {metric.numerator !== undefined && metric.numerator !== null && (
                <div className="flex justify-between items-center pt-1 text-slate-300">
                  <span>Numerator:</span>
                  <span className="font-bold text-blue-400">{metric.numerator}</span>
                </div>
              )}
              {metric.denominator !== undefined && metric.denominator !== null && (
                <div className="flex justify-between items-center text-slate-300">
                  <span>Denominator:</span>
                  <span className="font-bold text-blue-400">{metric.denominator}</span>
                </div>
              )}
            </div>
          </div>

          {/* Results Summary & Display Index */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Raw Measurement</span>
              <div className="text-base font-bold font-mono text-slate-100 mt-0.5">
                {metric.raw_value !== null ? `${metric.raw_value} ${metric.raw_unit}` : 'Not available'}
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-blue-900/40 rounded-xl">
              <span className="text-[10px] text-blue-400 uppercase font-semibold">{metric.index_label}</span>
              <div className="text-base font-bold font-mono text-blue-300 mt-0.5">
                {metric.display_index !== null ? `${metric.display_index.toFixed(1)} / 100` : 'Not available'}
              </div>
            </div>
          </div>

          {/* Provenance & Methodology */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-300">
              <Info className="w-3.5 h-3.5 text-blue-400" />
              Methodology & Scientific Meaning
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
              {metric.provenance}
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
