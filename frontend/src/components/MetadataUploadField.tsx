import React, { useState, useRef } from 'react';
import {
  FileCode,
  Upload,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Trash2,
  Info
} from 'lucide-react';
import { MetadataStatus, MetadataParseResult } from '../types';

interface MetadataUploadFieldProps {
  role: 'source' | 'reference';
  label: string; // e.g. "OHRC Metadata" or "LRO NAC Metadata"
  sublabel: string; // e.g. ".xml (OHRC/PDS4), .lbl (PDS3), .json"
  accentColor: 'emerald' | 'blue';
  file: File | null;
  parseResult: MetadataParseResult | null;
  status: MetadataStatus;
  statusDetails: string;
  onFileSelect: (file: File) => void;
  onRemove: () => void;
  onReplace: () => void;
}

export const MetadataUploadField: React.FC<MetadataUploadFieldProps> = ({
  role,
  label,
  sublabel,
  accentColor,
  file,
  parseResult,
  status,
  statusDetails,
  onFileSelect,
  onRemove,
  onReplace
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEmerald = accentColor === 'emerald';

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      const name = droppedFile.name.toLowerCase();
      if (name.endsWith('.xml') || name.endsWith('.lbl') || name.endsWith('.json')) {
        onFileSelect(droppedFile);
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const renderStatusBadge = () => {
    switch (status) {
      case 'Processing Metadata':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-950/60 text-amber-300 border border-amber-500/30 shadow-xs">
            <Loader2 className="w-3 h-3 animate-spin text-amber-400" />
            <span>Processing Metadata</span>
          </span>
        );
      case 'Metadata Matched':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shadow-xs">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>Metadata Matched</span>
          </span>
        );
      case 'Metadata Mismatch':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-950/60 text-rose-300 border border-rose-500/40 shadow-xs">
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            <span>Metadata Mismatch</span>
          </span>
        );
      case 'Invalid Metadata':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-950/60 text-rose-300 border border-rose-500/40 shadow-xs">
            <XCircle className="w-3 h-3 text-rose-400" />
            <span>Invalid Metadata</span>
          </span>
        );
      case 'Upload Successful':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-sky-950/60 text-sky-300 border border-sky-500/40 shadow-xs">
            <CheckCircle2 className="w-3 h-3 text-sky-400" />
            <span>Upload Successful</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="mt-4 pt-3 border-t border-slate-800/80">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleInputChange}
        accept=".xml,.lbl,.json,text/xml,application/json"
        className="hidden"
      />

      {/* Field Section Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <FileCode
            className={`w-3.5 h-3.5 ${isEmerald ? 'text-emerald-400' : 'text-blue-400'}`}
          />
          <span className="text-xs font-semibold text-slate-200">{label}</span>
          <span className="text-[10px] text-slate-500 font-mono">(.xml, .lbl, .json)</span>
        </div>
        {file && (
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => {
                if (fileInputRef.current) fileInputRef.current.click();
                onReplace();
              }}
              className="px-1.5 py-0.5 text-[10px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors flex items-center gap-1 cursor-pointer"
              title="Replace current metadata file"
            >
              <RefreshCw className="w-2.5 h-2.5" />
              <span>Replace</span>
            </button>
            <button
              type="button"
              onClick={onRemove}
              className="px-1.5 py-0.5 text-[10px] text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 rounded transition-colors flex items-center gap-1 cursor-pointer"
              title="Remove metadata file"
            >
              <Trash2 className="w-2.5 h-2.5" />
              <span>Remove</span>
            </button>
          </div>
        )}
      </div>

      {!file ? (
        /* Compact Drag & Drop Box when empty */
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`flex items-center justify-between py-2.5 px-3 rounded-xl border border-dashed transition-all cursor-pointer text-left group ${
            isDragging
              ? isEmerald
                ? 'border-emerald-400 bg-emerald-950/30'
                : 'border-blue-400 bg-blue-950/30'
              : isEmerald
              ? 'border-slate-800 hover:border-emerald-500/50 bg-slate-950/50 hover:bg-emerald-950/20'
              : 'border-slate-800 hover:border-blue-500/50 bg-slate-950/50 hover:bg-blue-950/20'
          }`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              className={`p-1.5 rounded-lg border transition-colors shrink-0 ${
                isEmerald
                  ? 'bg-slate-900 border-slate-800 group-hover:border-emerald-500/40 text-slate-400 group-hover:text-emerald-400'
                  : 'bg-slate-900 border-slate-800 group-hover:border-blue-500/40 text-slate-400 group-hover:text-blue-400'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <p
                className={`text-xs font-medium transition-colors truncate ${
                  isEmerald
                    ? 'text-slate-300 group-hover:text-emerald-300'
                    : 'text-slate-300 group-hover:text-blue-300'
                }`}
              >
                Choose {role === 'source' ? 'OHRC' : 'LRO NAC'} metadata file
              </p>
              <p className="text-[10px] text-slate-500 truncate">
                Drag & drop .xml, .lbl, or .json
              </p>
            </div>
          </div>
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded-md border shrink-0 transition-colors ${
              isEmerald
                ? 'bg-slate-900/80 border-slate-800 text-slate-400 group-hover:text-emerald-300 group-hover:border-emerald-500/30'
                : 'bg-slate-900/80 border-slate-800 text-slate-400 group-hover:text-blue-300 group-hover:border-blue-500/30'
            }`}
          >
            Browse
          </span>
        </div>
      ) : (
        /* Compact File Information and Validation Status Box */
        <div
          className={`p-2.5 rounded-xl border bg-slate-950/70 transition-all ${
            isEmerald
              ? 'border-emerald-500/30 shadow-xs shadow-emerald-950/30'
              : 'border-blue-500/30 shadow-xs shadow-blue-950/30'
          }`}
        >
          {/* File details & Status badge row */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 pb-2 border-b border-slate-800/70">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${
                  isEmerald ? 'bg-emerald-400' : 'bg-blue-400'
                }`}
              />
              <span className="text-xs font-medium text-slate-200 truncate max-w-[190px]" title={file.name}>
                {file.name}
              </span>
              <span className="text-[10px] text-slate-500 font-mono shrink-0">
                ({formatFileSize(file.size)})
              </span>
              {parseResult?.format && (
                <span className="hidden sm:inline text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                  {parseResult.format}
                </span>
              )}
            </div>
            <div className="shrink-0">{renderStatusBadge()}</div>
          </div>

          {/* Validation Details description */}
          {statusDetails && (
            <p className="mt-1.5 text-[11px] text-slate-400 leading-snug break-words">
              {statusDetails}
            </p>
          )}

          {/* Collapsible Metadata Preview Toggle */}
          <div className="mt-2 pt-2 border-t border-slate-800/60">
            <button
              type="button"
              onClick={() => setIsPreviewOpen(!isPreviewOpen)}
              className="w-full flex items-center justify-between text-[11px] font-medium text-slate-300 hover:text-white transition-colors cursor-pointer py-0.5"
            >
              <span className="flex items-center gap-1.5">
                <Info className="w-3 h-3 text-slate-400" />
                <span>Metadata Preview</span>
                <span className="text-[10px] text-slate-500 font-normal">
                  (7 extracted attributes)
                </span>
              </span>
              <span className="flex items-center gap-1 text-[10px] text-slate-400">
                <span>{isPreviewOpen ? 'Collapse' : 'Expand'}</span>
                {isPreviewOpen ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </span>
            </button>

            {/* Extracted 7 attributes preview table */}
            {isPreviewOpen && (
              <div className="mt-2 p-2 bg-slate-900/90 rounded-lg border border-slate-800 text-[11px] space-y-1.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-1.5">
                  {/* 1. Product ID */}
                  <div>
                    <span className="text-slate-500 block text-[10px]">Product ID</span>
                    <span className="text-slate-200 font-mono break-all font-medium">
                      {parseResult?.metadata?.product_id || '—'}
                    </span>
                  </div>

                  {/* 2. Instrument ID */}
                  <div>
                    <span className="text-slate-500 block text-[10px]">Instrument ID</span>
                    <span
                      className={`font-medium ${
                        isEmerald ? 'text-emerald-400' : 'text-blue-400'
                      }`}
                    >
                      {parseResult?.metadata?.instrument_id || '—'}
                    </span>
                  </div>

                  {/* 3. Acquisition date/time */}
                  <div>
                    <span className="text-slate-500 block text-[10px]">Acquisition Date/Time</span>
                    <span className="text-slate-200 font-mono">
                      {parseResult?.metadata?.acquisition_time || '—'}
                    </span>
                  </div>

                  {/* 4. Image filename */}
                  <div>
                    <span className="text-slate-500 block text-[10px]">Declared Image Filename</span>
                    <span className="text-slate-200 font-mono break-all">
                      {parseResult?.metadata?.image_filename || '— (Inferred from archive)'}
                    </span>
                  </div>

                  {/* 5. Image width and height */}
                  <div>
                    <span className="text-slate-500 block text-[10px]">Image Dimensions (W × H)</span>
                    <span className="text-slate-200 font-mono">
                      {parseResult?.metadata?.width && parseResult?.metadata?.height
                        ? `${parseResult.metadata.width.toLocaleString()} × ${parseResult.metadata.height.toLocaleString()} px`
                        : '—'}
                    </span>
                  </div>

                  {/* 6. Pixel data type */}
                  <div>
                    <span className="text-slate-500 block text-[10px]">Pixel Data Type</span>
                    <span className="text-slate-200 font-mono">
                      {parseResult?.metadata?.pixel_data_type || '—'}
                    </span>
                  </div>

                  {/* 7. Resolution */}
                  <div className="sm:col-span-2">
                    <span className="text-slate-500 block text-[10px]">Resolution / GSD</span>
                    <span className="text-slate-200 font-mono">
                      {parseResult?.metadata?.resolution || '—'}
                    </span>
                  </div>
                </div>

                {/* Optional Raw Fields Toggle */}
                {parseResult?.raw_fields && Object.keys(parseResult.raw_fields).length > 0 && (
                  <div className="pt-1.5 border-t border-slate-800/80">
                    <button
                      type="button"
                      onClick={() => setShowRaw(!showRaw)}
                      className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                    >
                      {showRaw ? 'Hide raw label parameters' : 'Show raw label parameters'}
                    </button>
                    {showRaw && (
                      <pre className="mt-1 p-1.5 bg-slate-950 rounded text-[9px] text-slate-400 font-mono max-h-36 overflow-y-auto whitespace-pre-wrap">
                        {JSON.stringify(parseResult.raw_fields, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
