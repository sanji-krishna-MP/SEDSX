import React, { useState } from 'react';
import { Layers, Eye, ShieldCheck, Image as ImageIcon } from 'lucide-react';
import { RunSummary } from '../types';

interface OriginalsPreviewProps {
  run: RunSummary;
  assets: Record<string, string>;
}

export const OriginalsPreview: React.FC<OriginalsPreviewProps> = ({ run, assets }) => {
  const [refLayer, setRefLayer] = useState<'preprocessed' | 'mask' | 'original'>('preprocessed');
  const [srcLayer, setSrcLayer] = useState<'preprocessed' | 'mask' | 'original'>('preprocessed');

  const getRefImgUrl = () => {
    if (refLayer === 'mask') return assets.reference_mask;
    if (refLayer === 'original') return `/api/runs/${run.id}/assets/reference_original`;
    return assets.reference_preprocessed || `/api/runs/${run.id}/assets/reference_original`;
  };

  const getSrcImgUrl = () => {
    if (srcLayer === 'mask') return assets.source_mask;
    if (srcLayer === 'original') return `/api/runs/${run.id}/assets/source_original`;
    return assets.source_preprocessed || `/api/runs/${run.id}/assets/source_original`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Top Center: Reference LRO NAC */}
      <div className="card p-3.5 bg-slate-900/90 border-slate-800 flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm shadow-blue-500/50" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Reference: LRO NAC
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              ({run.ref_dims ? `${run.ref_dims[1]}×${run.ref_dims[0]}` : 'Loaded'})
            </span>
          </div>

          {/* Layer toggles */}
          <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={() => setRefLayer('preprocessed')}
              className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                refLayer === 'preprocessed' ? 'bg-slate-800 text-blue-400 shadow-xs' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Normalized
            </button>
            <button
              onClick={() => setRefLayer('mask')}
              className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                refLayer === 'mask' ? 'bg-slate-800 text-blue-400 shadow-xs' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Mask
            </button>
            <button
              onClick={() => setRefLayer('original')}
              className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                refLayer === 'original' ? 'bg-slate-800 text-blue-400 shadow-xs' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Raw
            </button>
          </div>
        </div>

        <div className="relative aspect-square max-h-56 bg-slate-950 rounded-lg overflow-hidden flex items-center justify-center border border-slate-800">
          <img
            src={getRefImgUrl()}
            alt="Reference LRO NAC preview"
            className="w-full h-full object-contain"
          />
          <div className="absolute bottom-2 left-2 bg-slate-900/90 backdrop-blur-xs text-slate-300 text-[10px] px-2 py-0.5 rounded font-mono border border-slate-800">
            {run.reference_filename}
          </div>
        </div>
      </div>

      {/* Top Right: Source OHRC */}
      <div className="card p-3.5 bg-slate-900/90 border-slate-800 flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Source: OHRC
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              ({run.source_dims ? `${run.source_dims[1]}×${run.source_dims[0]}` : 'Loaded'})
            </span>
          </div>

          {/* Layer toggles */}
          <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={() => setSrcLayer('preprocessed')}
              className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                srcLayer === 'preprocessed' ? 'bg-slate-800 text-emerald-400 shadow-xs' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Normalized
            </button>
            <button
              onClick={() => setSrcLayer('mask')}
              className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                srcLayer === 'mask' ? 'bg-slate-800 text-emerald-400 shadow-xs' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Mask
            </button>
            <button
              onClick={() => setSrcLayer('original')}
              className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                srcLayer === 'original' ? 'bg-slate-800 text-emerald-400 shadow-xs' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Raw
            </button>
          </div>
        </div>

        <div className="relative aspect-square max-h-56 bg-slate-950 rounded-lg overflow-hidden flex items-center justify-center border border-slate-800">
          <img
            src={getSrcImgUrl()}
            alt="Source OHRC preview"
            className="w-full h-full object-contain"
          />
          <div className="absolute bottom-2 left-2 bg-slate-900/90 backdrop-blur-xs text-slate-300 text-[10px] px-2 py-0.5 rounded font-mono border border-slate-800">
            {run.source_filename}
          </div>
        </div>
      </div>
    </div>
  );
};
