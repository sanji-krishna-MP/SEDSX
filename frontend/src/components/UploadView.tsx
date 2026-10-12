import React, { useState, useRef } from 'react';
import { Upload, ArrowLeftRight, Sliders, Play, PlayCircle, FileImage } from 'lucide-react';
import { MetadataUploadField } from './MetadataUploadField';
import { MetadataStatus, MetadataParseResult } from '../types';

interface UploadViewProps {
  onStartComparison: (formData: FormData) => void;
  isSubmitting: boolean;
  onLoadDemo?: () => void;
  isDemoLoading?: boolean;
}

export const UploadView: React.FC<UploadViewProps> = ({
  onStartComparison,
  isSubmitting,
  onLoadDemo,
  isDemoLoading = false,
}) => {
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [srcPreview, setSrcPreview] = useState<string | null>(null);
  const [refPreview, setRefPreview] = useState<string | null>(null);
  const [srcDims, setSrcDims] = useState<{ width: number; height: number } | null>(null);
  const [refDims, setRefDims] = useState<{ width: number; height: number } | null>(null);

  // Dedicated Metadata states
  const [metadataSrcFile, setMetadataSrcFile] = useState<File | null>(null);
  const [metadataRefFile, setMetadataRefFile] = useState<File | null>(null);
  const [srcMetaParse, setSrcMetaParse] = useState<MetadataParseResult | null>(null);
  const [refMetaParse, setRefMetaParse] = useState<MetadataParseResult | null>(null);
  const [srcMetaStatus, setSrcMetaStatus] = useState<MetadataStatus>('idle');
  const [refMetaStatus, setRefMetaStatus] = useState<MetadataStatus>('idle');
  const [srcMetaDetails, setSrcMetaDetails] = useState<string>('');
  const [refMetaDetails, setRefMetaDetails] = useState<string>('');

  // Optional masks & checkpoints
  const [maskSrcFile, setMaskSrcFile] = useState<File | null>(null);
  const [maskRefFile, setMaskRefFile] = useState<File | null>(null);
  const [checkpointsFile, setCheckpointsFile] = useState<File | null>(null);

  // Advanced Config Drawer
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [e0Anchor, setE0Anchor] = useState<number>(1.0);
  const [r0Anchor, setR0Anchor] = useState<number>(1.0);
  const [ratioThresh, setRatioThresh] = useState<number>(0.75);
  const [ransacCutoff, setRansacCutoff] = useState<number>(3.0);
  const [gridSize, setGridSize] = useState<number>(4);

  const srcInputRef = useRef<HTMLInputElement>(null);
  const refInputRef = useRef<HTMLInputElement>(null);

  // Streaming metadata parser and validator
  const handleParseMetadata = async (
    file: File,
    role: 'source' | 'reference',
    currentImageFile?: File | null,
    currentDims?: { width: number; height: number } | null
  ) => {
    if (role === 'source') {
      setMetadataSrcFile(file);
      setSrcMetaStatus('Processing Metadata');
      setSrcMetaDetails('Streaming XML/label and extracting parameters...');
    } else {
      setMetadataRefFile(file);
      setRefMetaStatus('Processing Metadata');
      setRefMetaDetails('Streaming XML/label and extracting parameters...');
    }

    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('expected_role', role);

      const targetImg = role === 'source' ? (currentImageFile !== undefined ? currentImageFile : sourceFile) : (currentImageFile !== undefined ? currentImageFile : referenceFile);
      const targetDims = role === 'source' ? (currentDims !== undefined ? currentDims : srcDims) : (currentDims !== undefined ? currentDims : refDims);

      if (targetImg) fd.append('image_filename', targetImg.name);
      if (targetDims?.width) fd.append('image_width', String(targetDims.width));
      if (targetDims?.height) fd.append('image_height', String(targetDims.height));

      const res = await fetch('/api/metadata/parse', {
        method: 'POST',
        body: fd,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const status = (errData.status as MetadataStatus) || 'Invalid Metadata';
        const label = errData.status_label || `Failed to parse ${file.name}`;
        if (role === 'source') {
          setSrcMetaStatus(status);
          setSrcMetaDetails(label);
        } else {
          setRefMetaStatus(status);
          setRefMetaDetails(label);
        }
        return;
      }

      const data: MetadataParseResult = await res.json();
      if (role === 'source') {
        setSrcMetaParse(data);
        setSrcMetaStatus(data.status);
        setSrcMetaDetails(data.status_label || '');
      } else {
        setRefMetaParse(data);
        setRefMetaStatus(data.status);
        setRefMetaDetails(data.status_label || '');
      }
    } catch (e: any) {
      const msg = e?.message || 'Error communicating with metadata parser';
      if (role === 'source') {
        setSrcMetaStatus('Invalid Metadata');
        setSrcMetaDetails(msg);
      } else {
        setRefMetaStatus('Invalid Metadata');
        setRefMetaDetails(msg);
      }
    }
  };

  const handleSourceSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSourceFile(file);
      const url = URL.createObjectURL(file);
      setSrcPreview(url);

      const img = new Image();
      img.onload = () => {
        const dims = { width: img.naturalWidth, height: img.naturalHeight };
        setSrcDims(dims);
        if (metadataSrcFile) {
          handleParseMetadata(metadataSrcFile, 'source', file, dims);
        }
      };
      img.src = url;
    }
  };

  const handleRefSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setReferenceFile(file);
      const url = URL.createObjectURL(file);
      setRefPreview(url);

      const img = new Image();
      img.onload = () => {
        const dims = { width: img.naturalWidth, height: img.naturalHeight };
        setRefDims(dims);
        if (metadataRefFile) {
          handleParseMetadata(metadataRefFile, 'reference', file, dims);
        }
      };
      img.src = url;
    }
  };

  const handleSwapRoles = () => {
    const tmpF = sourceFile;
    const tmpP = srcPreview;
    const tmpD = srcDims;
    setSourceFile(referenceFile);
    setSrcPreview(refPreview);
    setSrcDims(refDims);
    setReferenceFile(tmpF);
    setRefPreview(tmpP);
    setRefDims(tmpD);

    // Swap metadata files & revalidate
    const tmpMetaF = metadataSrcFile;
    const tmpMetaParse = srcMetaParse;
    setMetadataSrcFile(metadataRefFile);
    setSrcMetaParse(refMetaParse);
    setMetadataRefFile(tmpMetaF);
    setRefMetaParse(tmpMetaParse);

    if (metadataRefFile) {
      handleParseMetadata(metadataRefFile, 'source', referenceFile, refDims);
    } else {
      setSrcMetaStatus('idle');
      setSrcMetaDetails('');
    }

    if (tmpMetaF) {
      handleParseMetadata(tmpMetaF, 'reference', tmpF, tmpD);
    } else {
      setRefMetaStatus('idle');
      setRefMetaDetails('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceFile || !referenceFile) return;

    const fd = new FormData();
    fd.append('source_file', sourceFile);
    fd.append('reference_file', referenceFile);

    if (metadataSrcFile) {
      fd.append('metadata_source_file', metadataSrcFile);
      if (srcMetaParse?.normalized_metadata) {
        fd.append('metadata_source', JSON.stringify(srcMetaParse.normalized_metadata));
      }
    }
    if (metadataRefFile) {
      fd.append('metadata_reference_file', metadataRefFile);
      if (refMetaParse?.normalized_metadata) {
        fd.append('metadata_reference', JSON.stringify(refMetaParse.normalized_metadata));
      }
    }
    if (maskSrcFile) fd.append('mask_source', maskSrcFile);
    if (maskRefFile) fd.append('mask_reference', maskRefFile);
    if (checkpointsFile) fd.append('checkpoints_file', checkpointsFile);

    const configObj = {
      error_scale_e0: e0Anchor,
      error_scale_r0: r0Anchor,
      match_ratio_thresh: ratioThresh,
      ransac_reproj_thresh: ransacCutoff,
      grid_rows: gridSize,
      grid_cols: gridSize,
    };
    fd.append('config_json', JSON.stringify(configObj));

    onStartComparison(fd);
  };

  return (
    <div className="max-w-5xl mx-auto py-6 sm:py-8 px-4 sm:px-6 w-full">
      {/* Exact Page Heading & Subtitle */}
      <div className="text-center mb-6 sm:mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Compare Lunar Images
        </h2>
        <p className="mt-2 text-xs sm:text-sm text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Upload an OHRC source image and an LRO NAC reference image to evaluate their alignment.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Dual Upload Cards with Stacking-Safe Header Elements */}
        <div className="relative grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
          {/* Swap Roles Floating Button for desktop */}
          <div className="hidden md:flex absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
            <button
              type="button"
              onClick={handleSwapRoles}
              disabled={!sourceFile && !referenceFile}
              className="p-3 bg-slate-900 text-blue-400 hover:text-white hover:bg-blue-600 rounded-full border border-slate-700 shadow-xl hover:scale-105 active:scale-95 transition-all disabled:opacity-30 disabled:hover:scale-100 disabled:hover:bg-slate-900 cursor-pointer"
              title="Swap OHRC and LRO NAC roles"
            >
              <ArrowLeftRight className="w-4 h-4" />
            </button>
          </div>

          {/* LEFT CARD: OHRC source image */}
          <div className="card p-4 sm:p-5 bg-slate-900/90 border border-slate-800 hover:border-emerald-500/50 transition-colors flex flex-col rounded-2xl shadow-sm">
            {/* Separate elements for Card heading and secondary label to prevent any overlapping */}
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1.5 pb-3 mb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0 shadow-xs shadow-emerald-500/50" />
                <h3 className="font-semibold text-sm sm:text-base text-white tracking-wide truncate">
                  OHRC source image
                </h3>
              </div>
              <span className="text-xs font-normal text-slate-400 shrink-0 pl-4.5 sm:pl-0">
                Chandrayaan-2
              </span>
            </div>

            <input
              type="file"
              ref={srcInputRef}
              onChange={handleSourceSelect}
              accept="image/png,image/jpeg,image/tiff,.tif,.tiff"
              className="hidden"
            />

            {srcPreview ? (
              <div className="space-y-3 flex-1 flex flex-col justify-between">
                <div className="aspect-square max-h-56 bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center border border-slate-800 p-1">
                  <img src={srcPreview} alt="OHRC Source Preview" className="w-full h-full object-contain rounded-lg" />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-300 font-mono px-1">
                  <span className="truncate max-w-[200px] font-medium">{sourceFile?.name}</span>
                  <span className="text-slate-400 shrink-0">{((sourceFile?.size || 0) / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
                <button
                  type="button"
                  onClick={() => srcInputRef.current?.click()}
                  className="w-full py-2 text-xs text-slate-200 hover:text-white bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded-xl font-medium transition-colors cursor-pointer"
                >
                  Choose OHRC image
                </button>
              </div>
            ) : (
              <div
                onClick={() => srcInputRef.current?.click()}
                className="flex-1 flex flex-col items-center justify-center py-10 sm:py-12 px-4 rounded-xl border border-dashed border-slate-800 hover:border-emerald-500/50 bg-slate-950/40 hover:bg-slate-950/70 cursor-pointer text-slate-400 hover:text-emerald-400 transition-all text-center group"
              >
                <div className="p-3 rounded-full bg-slate-900 border border-slate-800 group-hover:border-emerald-500/40 group-hover:bg-emerald-950/30 transition-all mb-3">
                  <Upload className="w-6 h-6 text-slate-400 group-hover:text-emerald-400 transition-colors" />
                </div>
                <span className="text-xs sm:text-sm font-medium text-slate-200 group-hover:text-emerald-300 transition-colors">
                  Choose OHRC image
                </span>
                <span className="text-[11px] text-slate-500 mt-1.5 max-w-[220px]">
                  PNG, JPEG, single-band TIFF or GeoTIFF
                </span>
              </div>
            )}

            {/* Compact OHRC Metadata Upload Field directly below the existing Source Image — OHRC upload area */}
            <MetadataUploadField
              role="source"
              label="OHRC Metadata Upload"
              sublabel=".xml, .lbl, .json"
              accentColor="emerald"
              file={metadataSrcFile}
              parseResult={srcMetaParse}
              status={srcMetaStatus}
              statusDetails={srcMetaDetails}
              onFileSelect={(f) => handleParseMetadata(f, 'source')}
              onRemove={() => {
                setMetadataSrcFile(null);
                setSrcMetaParse(null);
                setSrcMetaStatus('idle');
                setSrcMetaDetails('');
              }}
              onReplace={() => {}}
            />
          </div>

          {/* Mobile Swap Button between stacked cards */}
          <div className="flex md:hidden justify-center -my-2 z-10">
            <button
              type="button"
              onClick={handleSwapRoles}
              disabled={!sourceFile && !referenceFile}
              className="px-3.5 py-1.5 bg-slate-900 text-blue-400 hover:text-white hover:bg-blue-600 rounded-full border border-slate-800 shadow-md text-xs font-medium flex items-center gap-1.5 disabled:opacity-30 cursor-pointer"
            >
              <ArrowLeftRight className="w-3.5 h-3.5" />
              <span>Swap roles</span>
            </button>
          </div>

          {/* RIGHT CARD: LRO NAC reference image */}
          <div className="card p-4 sm:p-5 bg-slate-900/90 border border-slate-800 hover:border-blue-500/50 transition-colors flex flex-col rounded-2xl shadow-sm">
            {/* Separate elements for Card heading and secondary label to prevent any overlapping */}
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1.5 pb-3 mb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shrink-0 shadow-xs shadow-blue-500/50" />
                <h3 className="font-semibold text-sm sm:text-base text-white tracking-wide truncate">
                  LRO NAC reference image
                </h3>
              </div>
              <span className="text-xs font-normal text-slate-400 shrink-0 pl-4.5 sm:pl-0">
                Lunar Reconnaissance Orbiter
              </span>
            </div>

            <input
              type="file"
              ref={refInputRef}
              onChange={handleRefSelect}
              accept="image/png,image/jpeg,image/tiff,.tif,.tiff"
              className="hidden"
            />

            {refPreview ? (
              <div className="space-y-3 flex-1 flex flex-col justify-between">
                <div className="aspect-square max-h-56 bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center border border-slate-800 p-1">
                  <img src={refPreview} alt="LRO NAC Reference Preview" className="w-full h-full object-contain rounded-lg" />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-300 font-mono px-1">
                  <span className="truncate max-w-[200px] font-medium">{referenceFile?.name}</span>
                  <span className="text-slate-400 shrink-0">{((referenceFile?.size || 0) / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
                <button
                  type="button"
                  onClick={() => refInputRef.current?.click()}
                  className="w-full py-2 text-xs text-slate-200 hover:text-white bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded-xl font-medium transition-colors cursor-pointer"
                >
                  Choose LRO NAC image
                </button>
              </div>
            ) : (
              <div
                onClick={() => refInputRef.current?.click()}
                className="flex-1 flex flex-col items-center justify-center py-10 sm:py-12 px-4 rounded-xl border border-dashed border-slate-800 hover:border-blue-500/50 bg-slate-950/40 hover:bg-slate-950/70 cursor-pointer text-slate-400 hover:text-blue-400 transition-all text-center group"
              >
                <div className="p-3 rounded-full bg-slate-900 border border-slate-800 group-hover:border-blue-500/40 group-hover:bg-blue-950/30 transition-all mb-3">
                  <Upload className="w-6 h-6 text-slate-400 group-hover:text-blue-400 transition-colors" />
                </div>
                <span className="text-xs sm:text-sm font-medium text-slate-200 group-hover:text-blue-300 transition-colors">
                  Choose LRO NAC image
                </span>
                <span className="text-[11px] text-slate-500 mt-1.5 max-w-[220px]">
                  PNG, JPEG, single-band TIFF or GeoTIFF
                </span>
              </div>
            )}

            {/* Compact LRO NAC Metadata Upload Field directly below the existing Reference Image — LRO NAC upload area */}
            <MetadataUploadField
              role="reference"
              label="LRO NAC Metadata Upload"
              sublabel=".xml, .lbl, .json"
              accentColor="blue"
              file={metadataRefFile}
              parseResult={refMetaParse}
              status={refMetaStatus}
              statusDetails={refMetaDetails}
              onFileSelect={(f) => handleParseMetadata(f, 'reference')}
              onRemove={() => {
                setMetadataRefFile(null);
                setRefMetaParse(null);
                setRefMetaStatus('idle');
                setRefMetaDetails('');
              }}
              onReplace={() => {}}
            />
          </div>
        </div>

        {/* Settings: “Metadata and processing options” | action: “Edit options” */}
        <div className="card p-4 sm:p-5 bg-slate-900/90 border border-slate-800 rounded-2xl">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between text-xs sm:text-sm font-medium text-slate-200 hover:text-white transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-400" />
              <span>Metadata and processing options</span>
            </span>
            <span className="text-blue-400 hover:text-blue-300 text-xs font-semibold px-2.5 py-1 rounded-md bg-blue-950/50 border border-blue-800/40 transition-colors">
              {showAdvanced ? 'Hide options' : 'Edit options'}
            </span>
          </button>

          {showAdvanced && (
            <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              {/* Checkpoints CSV */}
              <div className="space-y-1 sm:col-span-2 lg:col-span-3">
                <label className="font-medium text-slate-300 block">Independent Checkpoints (CSV)</label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setCheckpointsFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:bg-slate-800 file:text-slate-300 hover:file:bg-slate-700 cursor-pointer"
                />
                <p className="text-[11px] text-slate-500">checkpoint_id, source_x, source_y, reference_x, reference_y</p>
              </div>

              {/* Residual Anchor */}
              <div className="space-y-1">
                <label className="font-medium text-slate-300 block">Residual Scale Anchor e0 (px)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={e0Anchor}
                  onChange={(e) => setE0Anchor(parseFloat(e.target.value) || 1.0)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:border-blue-500 focus:outline-hidden"
                />
                <p className="text-[11px] text-slate-500">Normalizes median residual consistency index</p>
              </div>

              {/* Checkpoint Anchor */}
              <div className="space-y-1">
                <label className="font-medium text-slate-300 block">Checkpoint Scale Anchor r0 (px)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={r0Anchor}
                  onChange={(e) => setR0Anchor(parseFloat(e.target.value) || 1.0)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:border-blue-500 focus:outline-hidden"
                />
                <p className="text-[11px] text-slate-500">Normalizes checkpoint RMSE index</p>
              </div>

              {/* Ratio filter threshold */}
              <div className="space-y-1">
                <label className="font-medium text-slate-300 block">Ratio Filter Cutoff (d1/d2)</label>
                <input
                  type="number"
                  step="0.05"
                  min="0.4"
                  max="0.95"
                  value={ratioThresh}
                  onChange={(e) => setRatioThresh(parseFloat(e.target.value) || 0.75)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:border-blue-500 focus:outline-hidden"
                />
                <p className="text-[11px] text-slate-500">Candidate match ambiguity cutoff</p>
              </div>

              {/* RANSAC cutoff */}
              <div className="space-y-1">
                <label className="font-medium text-slate-300 block">Geometric Refinement Cutoff (px)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="15.0"
                  value={ransacCutoff}
                  onChange={(e) => setRansacCutoff(parseFloat(e.target.value) || 3.0)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:border-blue-500 focus:outline-hidden"
                />
                <p className="text-[11px] text-slate-500">Inlier acceptance reprojection threshold</p>
              </div>

              {/* Spatial grid */}
              <div className="space-y-1">
                <label className="font-medium text-slate-300 block">Spatial Grid Partition</label>
                <input
                  type="number"
                  min="2"
                  max="8"
                  value={gridSize}
                  onChange={(e) => setGridSize(parseInt(e.target.value) || 4)}
                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:border-blue-500 focus:outline-hidden"
                />
                <p className="text-[11px] text-slate-500">Grid cells (N×N) for spatial distribution</p>
              </div>
            </div>
          )}
        </div>

        {/* Action Bar: Main button “Start comparison” & Demo button “Load sample pair” */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          {onLoadDemo && (
            <button
              type="button"
              onClick={onLoadDemo}
              disabled={isDemoLoading || isSubmitting}
              className="px-4 py-2.5 rounded-xl font-medium text-xs text-blue-300 hover:text-white bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 hover:border-blue-500/50 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-sm order-2 sm:order-1"
              title="Load Bundled OHRC & LRO NAC Crater Demo Pair"
            >
              <PlayCircle className="w-4 h-4 text-blue-400" />
              <span>{isDemoLoading ? 'Loading sample pair...' : 'Load sample pair'}</span>
            </button>
          )}

          <div className="flex justify-end order-1 sm:order-2">
            <button
              type="submit"
              disabled={!sourceFile || !referenceFile || isSubmitting}
              className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2 text-xs uppercase tracking-wider transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <Play className="w-4 h-4" />
              <span>{isSubmitting ? 'Evaluating Alignment...' : 'Start comparison'}</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default UploadView;
